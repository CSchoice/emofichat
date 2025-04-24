from __future__ import annotations

import json
import backoff
from typing import Dict, Any, Tuple, Optional, List
import logging

from openai import (
    APITimeoutError, APIConnectionError, RateLimitError, BadRequestError
)
from sqlalchemy import select

from app.core.openai_client import client as openai_client
from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel
from app.services.scenario_engine import score_scenarios
# 템플릿 대신 GPT 직접 활용하므로 TEMPLATES 임포트 제거
from app.services.generic_chat import load_history, save_history
from app.services.generic_chat import get_generic_reply
from app.services.finance_analyzer import analyze_financial_trends
from app.services.data_fetcher import get_user_metrics

# 로거 설정
logger = logging.getLogger(__name__)

# ───────────────────── 공통 설정 ────────────────────── #
RETRY_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError)

# ───────────────────── 사용자 대화 요약 함수 ───────────────────── #
async def get_compact_history(user_id: str, max_history: int = 2) -> str:
    """사용자의 최근 대화 히스토리를 요약해서 가져오는 함수
    
    토큰 절약을 위해 최대 max_history개의 대화만 가져오고, 요약한 형태로 반환합니다.
    """
    try:
        # 기존 load_history 함수 활용
        history = await load_history(user_id)
        
        if not history or len(history) == 0:
            return ""
        
        # 최신 대화 max_history개만 가져오기 (현재 대화 제외)
        recent_history = history[-max_history:] if len(history) > max_history else history
        
        # 요약형 형태로 간결한 히스토리 구성
        compact_history = ""
        for idx, (user_q, bot_a) in enumerate(recent_history):
            keywords = extract_keywords(user_q)
            summary = summarize_response(bot_a)
            compact_history += f"\n최근 대화 {idx+1}: 질문 [{keywords}] / 답변 [{summary}]"
        
        return compact_history
    except Exception as e:
        logger.warning(f"사용자 {user_id} 히스토리 요약 오류: {str(e)}")
        return ""

def extract_keywords(text: str, max_words: int = 5) -> str:
    """사용자 질문에서 주요 키워드만 추출
    
    토큰 절약을 위해 질문을 간략하게 요약합니다.
    """
    # 짧은 질문은 그대로 반환
    if len(text.split()) <= max_words:
        return text
    
    # 재무 관련 키워드 정의
    finance_keywords = [
        "가계", "소득", "지출", "저축", "투자", "비용", "자산", "대출", "신용", "카드", "이자", "금액", "재테크", "연체", "재무", "은행", "상환", "보험", "연금", "주식", "카드", "기획", "경제", "보유", "자금", "가능", "공과", "적금", "재산"
    ]
    
    words = text.split()
    important_words = []
    
    # 재무 키워드 우선 추출
    for word in words:
        for keyword in finance_keywords:
            if keyword in word:
                important_words.append(word)
                break
        if len(important_words) >= max_words:
            break
    
    # 충분한 키워드가 없으면 질문에서 중요 단어 추가
    if len(important_words) < max_words:
        for word in words:
            if word not in important_words and ("?" in word or "요" in word):
                important_words.append(word)
            if len(important_words) >= max_words:
                break
    
    # 여전히 부족한 경우 나머지 단어 추가
    if len(important_words) < max_words:
        for word in words:
            if word not in important_words and len(word) > 1:  # 한 글자 이상인 단어만 추가
                important_words.append(word)
            if len(important_words) >= max_words:
                break
    
    return " ".join(important_words[:max_words])

def summarize_response(text: str, max_chars: int = 30) -> str:
    """챗봇 응답을 매우 간결하게 요약
    
    토큰 절약을 위해 응답을 간략하게 요약합니다.
    """
    if len(text) <= max_chars:
        return text
    
    # 접그마를 고려한 잘라내기
    if ". " in text[:max_chars]:
        return text[:max_chars].rsplit(". ", 1)[0] + "."
    else:
        return text[:max_chars] + "..."

# ───────────────────── 메인 엔드포인트 로직 ───────────────────── #
@backoff.on_exception(backoff.expo, RETRY_ERRORS, max_tries=3)
async def get_finance_reply(user_id: str, user_msg: str) -> Tuple[str, Optional[Dict]]:
    """
    금융 상담 챗봇의 메인 함수입니다.
    
    1️⃣ 사용자 지표(DB에서 조회)  
    2️⃣ 시나리오 스코어링 + 재무 트렌드 분석
    3️⃣ 이전 대화 히스토리 고려
    4️⃣ GPT-3.5로 맞춤형 조언 생성
    """
    try:
        # 사용자 지표 조회
        row = await get_user_metrics(user_id)
        if not row:
            # 지표가 없는 신규/테스트 계정 → 일반 채팅으로 폴백
            logger.warning(f"사용자 {user_id} 지표 없음. 일반 채팅으로 응답")
            reply = await get_generic_reply(user_id, user_msg)
            return reply, None

        # ── 시나리오 판단 ───────────────────────────────────────── #
        label, prob, metrics = score_scenarios(row, user_msg)
        
        # ── 재무 트렌드 분석 ──────────────────────────────────── #
        finance_trends = analyze_financial_trends(row)
        
        # ── 사용자 재무 데이터 요약 ───────────────────────────────── #
        # 중요 지표만 선별하여 GPT에 전달
        user_finance_summary = {
            "재무상태": label,  # 시나리오 라벨
            "나이": row.get("age", "정보없음"),
            "성별": row.get("gender", "정보없음"),
            "소득수준": row.get("income_level", "정보없음"),
            "직업": row.get("job_type", "정보없음"),
            "현재잔액": row.get("balance_b0m", 0),
            "3개월평균잔액": row.get("avg_balance_3m", 0),
            "최근카드사용액": row.get("card_usage_b0m", 0),
            "3개월평균카드사용액": row.get("avg_card_usage_3m", 0),
            "연체여부": row.get("is_delinquent", 0) == 1,
            "유동성점수": row.get("liquidity_score", 50.0),
            "잔액추세": finance_trends.get("balance_trend", "정보없음"),
            "카드사용추세": finance_trends.get("card_trend", "정보없음"),
            "재정건전성": finance_trends.get("financial_health", "정보없음"),
            "스트레스지수": finance_trends.get("stress_index", 50.0),
            "스트레스수준": finance_trends.get("stress_level", "보통"),
        }
        
        # ── 사용자 대화 히스토리 요약 가져오기 ───────────────────── #
        conversation_history = await get_compact_history(user_id)
        
        # ── GPT로 직접 맞춤형 조언 생성 ────────────────────────── #
        sys_prompt = (
            "너는 전문 재무 상담 챗봇이야. 사용자의 재무 데이터, 대화 맥락, 질문을 종합적으로 분석해서 구체적이고 실용적인 맞춤형 조언을 제공해야 해. "
            "답변은 친근한 한국어로 2~3문장, 숫자는 % 대신 '퍼센트' 표기, 어려운 금융 용어는 풀어서 설명해. "
            "사용자의 최근 대화 내용과 재무 트렌드를 고려하여 일관성 있고 개인화된 조언을 제공해주세요."
        )
        
        # 사용자 재무 데이터, 대화 히스토리, 질문을 함께 전달하여 맞춤형 조언 요청
        user_content = f"""[사용자 재무 데이터]
{user_finance_summary}

{conversation_history if conversation_history else ""}

[현재 질문]
{user_msg}"""
        
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content}
        ]

        try:
            resp = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                temperature=0.5,
                max_tokens=180,
                messages=messages,
            )
            reply = resp.choices[0].message.content.strip()
        except BadRequestError as e:
            # 프롬프트 오류 시 기본 응답 제공
            logger.error(f"OpenAI API 오류: {str(e)}")
            reply = f"재무 상태 '{label}'에 맞는 조언을 드리려 했으나 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        except Exception as e:
            # 기타 오류 시에도 기본 응답 제공
            logger.error(f"OpenAI API 호출 오류: {str(e)}")
            reply = f"재무 상태 '{label}'에 맞는 조언을 드리려 했으나 처리 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        # ── 결과 패키징 ─────────────────────────────────────────── #
        scenario_info = (
            {
                "label": label,
                "probability": round(prob, 3),
                "key_metrics": metrics,
            }
            if label != "no_issue"
            else None
        )

        # 히스토리 저장(Redis) 재활용
        try:
            await save_history(user_id, user_msg, reply)
        except Exception as e:
            logger.error(f"히스토리 저장 오류: {str(e)}")
            
        return reply, scenario_info
        
    except Exception as e:
        # 예상치 못한 오류 발생 시 일반 채팅으로 폴백
        logger.error(f"금융 채팅 처리 중 오류 발생: {str(e)}")
        reply = await get_generic_reply(user_id, user_msg)
        return reply, None
