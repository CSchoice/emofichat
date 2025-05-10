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
    recommend_deposit_products, recommend_fund_products,
    PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND
)

# 금융 데이터베이스 서비스 추가
from app.services.database.user_financial_service import get_user_financial_service
from app.services.database.bank_product_service import get_bank_product_service
from app.services.database.fund_service import get_fund_service
from app.services.database.saving_product_service import get_saving_product_service
  
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
    """사용자 데이터 조회 (금융 데이터베이스 우선, 없으면 기존 메트릭 사용)"""
    try:
        # 금융 데이터베이스에서 사용자 정보 조회 시도
        user_financial_service = get_user_financial_service()
        financial_summary = await user_financial_service.get_user_financial_summary(user_id)
        
        # 금융 데이터가 있으면 사용
        if "error" not in financial_summary:
            # 기존 형식에 맞게 변환
            row = {
                "user_id": user_id,
                "gender": financial_summary.get("user", {}).get("gender"),
                "age": financial_summary.get("user", {}).get("age"),
                "residence": financial_summary.get("user", {}).get("residence"),
                "workplace": financial_summary.get("user", {}).get("workplace"),
                
                # 잔액 정보
                "balance": financial_summary.get("balance", {}).get("balance", 0),
                "loan_balance": financial_summary.get("balance", {}).get("balance_loan", 0),
                
                # 카드 사용 정보
                "credit_card_count": financial_summary.get("card_usage", {}).get("credit_card_count", 0),
                "credit_usage": financial_summary.get("card_usage", {}).get("credit_usage_3m", 0),
                
                # 연체 정보
                "is_delinquent": financial_summary.get("delinquency", {}).get("is_delinquent") == "Y",
                "delinquent_amount": financial_summary.get("delinquency", {}).get("delinquent_balance", 0),
                
                # 시나리오 라벨
                "scenario_labels": financial_summary.get("scenario", {}).get("scenario_labels", ""),
                "dti": financial_summary.get("scenario", {}).get("dti_estimate", 0),
                "debt_ratio": financial_summary.get("scenario", {}).get("debt_ratio", 0),
                
                # 지출 패턴
                "spending_shopping": financial_summary.get("spending", {}).get("spending_shopping", 0),
                "spending_food": financial_summary.get("spending", {}).get("spending_food", 0),
                "spending_transport": financial_summary.get("spending", {}).get("spending_transport", 0),
                "spending_medical": financial_summary.get("spending", {}).get("spending_medical", 0),
                "life_stage": financial_summary.get("spending", {}).get("life_stage", "")
            }
            
            # 금융 건강 정보 추가
            financial_health = financial_summary.get("financial_health", {})
            row["financial_health_score"] = financial_health.get("score", 50)
            row["financial_health_grade"] = financial_health.get("grade", "보통")
            
            return row
    except Exception as e:
        logger.error(f"금융 데이터베이스 조회 오류: {str(e)}")
    
    # 금융 데이터베이스에서 조회 실패 시 기존 메트릭 사용
    return await get_user_metrics(user_id)

def format_user_content(
    row: Dict[str, Any],
    finance_trends: Dict[str, Any],
    user_profile: Dict[str, Any],
    history_str: str,
    user_msg: str,
    emotion_data: Dict[str, Any]
) -> str:
    # 금융 데이터베이스에서 가져온 정보를 정확하게 반영
    user_finance_summary = {
        "재무성향": user_profile.get("재무성향", "정보없음"),
        "금융단계": user_profile.get("금융단계", "정보없음"),
        "스트레스반응": user_profile.get("스트레스반응", "정보없음"),
        "나이": row.get("age", "정보없음"),
        "성별": row.get("gender", "정보없음"),
        "현재잔액": row.get("balance", 0),  # 금융 DB에서 가져온 잔액 정보 사용
        "대출잔액": row.get("loan_balance", 0),  # 금융 DB에서 가져온 대출 잔액 정보 사용
        "카드사용액": row.get("credit_usage", 0),  # 금융 DB에서 가져온 카드 사용액 정보 사용
        "연체여부": bool(row.get("is_delinquent", 0)),
        "금융건강점수": row.get("financial_health_score", 50),  # 금융 건강 점수 추가
        "금융건강등급": row.get("financial_health_grade", "보통"),  # 금융 건강 등급 추가
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
        "너는 전문 재무 상담 챗봇이야. 사용자의 재무 데이터와 질문을 정확하게 이해하고 종합해서 "
        "구체적이고 실용적인 조언을 제공해야 해. "
        "사용자의 잔액, 대출잔액, 카드사용액, 금융건강점수 등의 정보를 정확하게 인용해서 응답해야 해. "
        "특히 사용자가 잔액이나 금융 상태에 대해 물어보면 정확한 수치를 알려주어야 해."
    )
    
    if is_delinquent:
        prompt += " 사용자가 연체 상태이므로 신용 관리와 부채 해결에 대한 조언을 포함해야 해."
    elif stress_index > 80:
        prompt += " 사용자의 재무 스트레스가 높으므로 재무 건강을 개선하기 위한 구체적인 조언을 포함해야 해."
    
    # 금융 건강 등급에 따른 추가 지침
    prompt += " 사용자의 금융 건강 상태에 맞는 맞춤형 조언을 제공해야 해."
    
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
    # 1) "추천"만 들어가면 무조건 예·적금 3개 추천
    if "추천" in user_msg:
        emotion_data = analyze_emotion(user_msg)
        # 키워드에 따라 상품 유형 결정
        if any(x in user_msg for x in ("펀드", "투자")):
            ptype = PRODUCT_TYPE_FUND
        elif any(x in user_msg for x in ("적금", "예금", "저축")):
            ptype = PRODUCT_TYPE_DEPOSIT
        else:
            ptype = PRODUCT_TYPE_DEPOSIT  # 기본값은 예적금

        # 금융 데이터베이스에서 추천 상품 조회 시도
        try:
            if ptype == PRODUCT_TYPE_DEPOSIT:
                # 적금 상품 서비스 사용
                saving_product_service = get_saving_product_service()
                db_products = await saving_product_service.recommend_products_for_user(user_id, limit=3)
                
                if db_products and not any("error" in p for p in db_products):
                    # 적금 상품 형식 변환
                    products = []
                    for p in db_products:
                        product = {
                            "name": p.get("fin_prdt_nm", ""),
                            "bank": p.get("company", {}).get("kor_co_nm", ""),
                            "interest_rate": p.get("max_rate", 0),
                            "description": f"최대 한도: {p.get('max_limit', 0):,}원",
                            "score": p.get("score", 0.5),
                            "reasons": p.get("reasons", [])
                        }
                        products.append(product)
                else:
                    # 기존 방식으로 대체
                    row = await get_user_data(user_id) or {}
                    products = await recommend_deposit_products(user_id, row, emotion_data, limit=3)
            elif ptype == PRODUCT_TYPE_FUND:
                # 펀드 서비스 사용
                fund_service = get_fund_service()
                db_products = await fund_service.recommend_funds_for_user(user_id, limit=3)
                
                if db_products and not any("error" in p for p in db_products):
                    # 펀드 상품 형식 변환
                    products = []
                    for p in db_products:
                        product = {
                            "name": p.get("fund_name", ""),
                            "company": p.get("company", {}).get("company_name", ""),
                            "type": p.get("type", {}).get("large_category", ""),
                            "return_1y": p.get("performance", {}).get("return_1y", 0) if p.get("performance") else 0,
                            "risk": "높음" if p.get("type", {}).get("large_category") == "주식형" else "중간" if p.get("type", {}).get("large_category") == "혼합형" else "낮음",
                            "score": p.get("score", 0.5),
                            "reasons": p.get("reasons", [])
                        }
                        products.append(product)
                else:
                    # 기존 방식으로 대체
                    row = await get_user_data(user_id) or {}
                    products = await recommend_fund_products(user_id, row, emotion_data, limit=3)
            else:
                products = []
        except Exception as e:
            logger.error(f"금융 데이터베이스 추천 오류: {str(e)}")
            # 오류 발생 시 기존 방식으로 대체
            row = await get_user_data(user_id) or {}
            if ptype == PRODUCT_TYPE_DEPOSIT:
                products = await recommend_deposit_products(user_id, row, emotion_data, limit=3)
            elif ptype == PRODUCT_TYPE_FUND:
                products = await recommend_fund_products(user_id, row, emotion_data, limit=3)
            else:
                products = []
                
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
    
    # 잔액 조회 관련 키워드가 있는지 확인
    is_balance_query = any(keyword in user_msg.lower() for keyword in [
        "잔액", "얼마", "얼마야", "얼마있어", "얼마남았", "얼마있지", "얼마있니",
        "계좌", "통장", "예금", "돈", "재산", "자산", "재정"
    ])
    
    # 대출 관련 키워드가 있는지 확인
    is_loan_query = any(keyword in user_msg.lower() for keyword in [
        "대출", "빚", "사채", "빚은", "빚은얼마", "빚은얼마야", "빚은얼마있어"
    ])
    
    # 금융 건강 관련 키워드가 있는지 확인
    is_health_query = any(keyword in user_msg.lower() for keyword in [
        "건강", "점수", "등급", "상태", "평가", "재무상태", "금융상태"
    ])
    
    # 연체 관련 키워드가 있는지 확인
    is_delinquent_query = any(keyword in user_msg.lower() for keyword in [
        "연체", "지불지체", "지불연체", "연체여부", "연체중"
    ])
    
    # 특별한 질문에 대한 추가 정보 제공
    additional_info = ""
    if is_balance_query:
        additional_info += f"\n\n[\uc794액 정보]\n현재 잔액: {row.get('balance', 0):,}원\n"
    if is_loan_query:
        additional_info += f"\n\n[대출 정보]\n대출 잔액: {row.get('loan_balance', 0):,}원\n"
    if is_health_query:
        additional_info += f"\n\n[금융 건강 정보]\n금융 건강 점수: {row.get('financial_health_score', 50)}점\n금융 건강 등급: {row.get('financial_health_grade', '보통')}\n"
    if is_delinquent_query:
        is_delinquent = bool(row.get("is_delinquent", False))
        delinquent_status = "연체 중" if is_delinquent else "연체 없음"
        additional_info += f"\n\n[연체 정보]\n연체 여부: {delinquent_status}\n"
    
    # 시스템 프롬프트에 추가 정보 추가
    sys_prompt = build_finance_chat_prompt(
        label=label,
        is_delinquent=bool(row.get("is_delinquent")),
        stress_index=finance_trends.get("stress_index", 0)
    )
    
    # 사용자 프롬프트에 추가 정보 추가
    user_content = format_user_content(
        row, finance_trends, user_profile, history_str, user_msg, emotion_data
    )

    # 추가 정보가 있는 경우 사용자 컨텐츠에 추가
    if additional_info:
        user_content += "\n\n[중요 금융 정보]" + additional_info
    
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
