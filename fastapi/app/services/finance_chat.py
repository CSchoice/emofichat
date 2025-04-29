from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple, List

import backoff
from openai import APITimeoutError, APIConnectionError, RateLimitError, BadRequestError

from app.core.openai_client import client as openai_client
from app.services.scenario_engine import score_scenarios
from app.services.topic_detector import analyze_emotion
from app.services.generic_chat import load_history, save_history, get_generic_reply
from app.services.finance_analyzer import analyze_financial_trends
from app.services.data_fetcher import get_user_metrics
from app.services.product_recommender import (
    recommend_products,
    PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND
)
from app.services.product_formatter import format_product_recommendation

# ───────────────────── 상수 정의 ────────────────────── #
MAX_HISTORY = 2
MAX_HISTORY_KEYWORDS = 5
SUMMARY_MAX_CHARS = 30

GPT_MODEL = "gpt-3.5-turbo-0125"
GPT_TEMPERATURE = 0.5
GPT_MAX_TOKENS = 1500

RETRY_EXCEPTIONS = (APITimeoutError, APIConnectionError, RateLimitError)

# ───────────────────── 로거 설정 ────────────────────── #
logger = logging.getLogger(__name__)

# ───────────────────── 유틸리티 함수 ────────────────────── #
def extract_keywords(text: str, max_words: int = MAX_HISTORY_KEYWORDS) -> str:
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])

def summarize_response(text: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    if ". " in text[:max_chars]:
        return text[:max_chars].rsplit(". ", 1)[0] + "."
    return text[:max_chars] + "..."

async def get_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """get_user_metrics 래퍼 (None 반환 가능)"""
    return await get_user_metrics(user_id)

def format_user_content(
    row: Dict[str, Any],
    finance_trends: Dict[str, Any],
    user_profile: Dict[str, Any],
    history_str: str,
    user_msg: str,
    emotion_data: Dict[str, Any]
) -> str:
    user_finance_summary = {
        "재무성향": user_profile.get("재무성향", "정보없음"),
        "금융단계": user_profile.get("금융단계", "정보없음"),
        "스트레스반응": user_profile.get("스트레스반응", "정보없음"),
        "나이": row.get("age", "정보없음"),
        "성별": row.get("gender", "정보없음"),
        "현재잔액": row.get("balance_b0m", 0),
        "3개월평균잔액": row.get("avg_balance_3m", 0),
        "최근카드사용액": row.get("card_usage_b0m", 0),
        "연체여부": bool(row.get("is_delinquent", 0)),
        "감정상태": emotion_data.get("dominant_emotion", "중립"),
    }
    parts = [
        "[사용자 재무 데이터]",
        json.dumps(user_finance_summary, ensure_ascii=False),
        "[사용자 성향 프로필]",
        json.dumps(user_profile, ensure_ascii=False),
    ]
    if history_str:
        parts.append(history_str)
    parts += ["[현재 질문]", user_msg]
    return "\n".join(parts)

def infer_user_profile(
    row: Dict[str, Any],
    finance_trends: Dict[str, Any],
    conversation_history: str,
    user_msg: str,
    emotion_data: Dict[str, Any]
) -> Dict[str, Any]:
    profile: Dict[str, Any] = {}
    # 재무성향
    if row.get("liquidity_score", 50) > 70 and finance_trends.get("balance_trend") == "지속 증가":
        profile["재무성향"] = "보수적 소비자"
    elif row.get("card_usage_b0m", 0) > row.get("avg_balance_3m", 0) * 1.2:
        profile["재무성향"] = "과소비 경향"
    else:
        profile["재무성향"] = "일반 소비자"
    # 금융단계
    age = row.get("age", 35)
    if age < 30:
        profile["금융단계"] = "사회초년생"
    elif age < 45:
        profile["금융단계"] = "자산형성기"
    elif age < 55:
        profile["금융단계"] = "자녀양육기"
    else:
        profile["금융단계"] = "은퇴준비기"
    # 스트레스반응
    dom = emotion_data.get("dominant_emotion", "중립")
    if dom in ("화남", "슬픔", "공포", "걱정"):
        profile["스트레스반응"] = f"{dom} 감정에 따른 대응"
    else:
        profile["스트레스반응"] = "문제 자체 해결 성향"
    return profile

def build_finance_chat_prompt(label: str, is_delinquent: bool, stress_index: float) -> str:
    prompt = (
        "너는 전문 재무 상담 챗봇이야. 사용자의 재무 데이터와 질문을 종합해 "
        "구체적이고 실용적인 조언을 제공해야 해."
    )
    if is_delinquent or stress_index > 80:
        prompt += " 현재 사용자의 재무 상태가 위험하니, 경고성 있는 조언을 해줘."
    return prompt

async def call_openai(messages: List[Dict[str, Any]]) -> str:
    resp = await openai_client.chat.completions.create(
        model=GPT_MODEL,
        temperature=GPT_TEMPERATURE,
        max_tokens=GPT_MAX_TOKENS,
        messages=messages,
    )
    return resp.choices[0].message.content.strip()

@backoff.on_exception(backoff.expo, RETRY_EXCEPTIONS, max_tries=3)
async def get_finance_reply(user_id: str, user_msg: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    # 1) “추천”만 들어가면 무조건 예·적금 3개 추천
    if "추천" in user_msg:
        emotion_data = analyze_emotion(user_msg)
        # “펀드” 혹은 “투자” 키워드가 없으면 deposit
        if any(x in user_msg for x in ("펀드", "투자")):
            ptype = PRODUCT_TYPE_FUND
        else:
            ptype = PRODUCT_TYPE_DEPOSIT

        row = await get_user_data(user_id) or {}
        products = await recommend_products(user_id, row, emotion_data, ptype, limit=3)
        formatted_response = format_product_recommendation(products, ptype, emotion_data)
        return formatted_response, None

    # 2) 그 외에는 일반 대화 흐름
    row = await get_user_data(user_id)
    if not row:
        reply = await get_generic_reply(user_id, user_msg)
        return reply, None

    emotion_data = analyze_emotion(user_msg)
    label, prob, metrics = score_scenarios(row, user_msg)
    finance_trends = analyze_financial_trends(row)

    hist = await load_history(user_id) or []
    history_str = "\n".join(
        f"대화 {i+1}: Q[{extract_keywords(q)}] / A[{summarize_response(a)}]"
        for i, (q, a) in enumerate(hist[-MAX_HISTORY:])
    )

    user_profile = infer_user_profile(row, finance_trends, history_str, user_msg, emotion_data)

    sys_prompt = build_finance_chat_prompt(
        label=label,
        is_delinquent=bool(row.get("is_delinquent")),
        stress_index=finance_trends.get("stress_index", 0)
    )
    user_content = format_user_content(
        row, finance_trends, user_profile, history_str, user_msg, emotion_data
    )

    try:
        raw_reply = await call_openai([
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_content}
        ])
    except BadRequestError:
        return f"[{label}] 처리 중 오류가 발생했습니다. 나중에 다시 시도해주세요.", None

    # 3) 히스토리 저장
    try:
        await save_history(user_id, user_msg, raw_reply)
    except Exception as e:
        logger.error(f"히스토리 저장 실패: {e}")

    info = (
        {"label": label, "probability": round(prob, 3), "key_metrics": metrics}
        if label != "no_issue" else None
    )
    return raw_reply, info
