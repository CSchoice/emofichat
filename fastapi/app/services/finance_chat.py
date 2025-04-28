from __future__ import annotations

import json
import backoff
from typing import Dict, Any, Tuple, Optional, List
import logging
import time

from openai import (
    APITimeoutError, APIConnectionError, RateLimitError, BadRequestError
)
from sqlalchemy import select

from app.core.openai_client import client as openai_client
from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel
from app.services.scenario_engine import score_scenarios
from app.services.topic_detector import analyze_emotion, analyze_message
# 템플릿 대신 GPT 직접 활용하므로 TEMPLATES 임포트 제거
from app.services.generic_chat import load_history, save_history
from app.services.generic_chat import get_generic_reply
from app.services.finance_analyzer import analyze_financial_trends
from app.services.data_fetcher import get_user_metrics
from app.services.product_recommender import recommend_products, format_product_recommendation, PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND

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
    5️⃣ 필요 시 금융 상품 추천
    """
    try:
        # 사용자 지표 조회
        row = await get_user_metrics(user_id)
        if not row:
            # 지표가 없는 신규/테스트 계정 → 일반 채팅으로 폴백
            logger.warning(f"사용자 {user_id} 지표 없음. 일반 채팅으로 응답")
            reply = await get_generic_reply(user_id, user_msg)
            return reply, None

        # ── 감정 분석 ─────────────────────────────────────────── #
        emotion_start = time.time()
        emotion_data = analyze_emotion(user_msg)
        logger.debug(f"감정 분석 소요 시간: {time.time() - emotion_start:.2f}초")
        
        # ── 시나리오 판단 ───────────────────────────────────────── #
        label, prob, metrics = score_scenarios(row, user_msg)
        
        # ── 사용자 재무 데이터 요약 및 트렌드 분석 ───────────────────── #
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
            "감정상태": emotion_data.get("dominant_emotion", "중립"),
            "부정감정수준": "높음" if emotion_data.get("is_negative", False) else "낮음",
            "불안감정수준": "높음" if emotion_data.get("is_anxious", False) else "낮음",
        }
        
        # ── 사용자 대화 히스토리 요약 가져오기 ───────────────────── #
        conversation_history = await get_compact_history(user_id)
        
        # ── 1. 개인화된 재무 캐릭터 모델 생성 ───────────────────── #
        # 사용자 재무 데이터와 감정 분석 결과에 기반하여 성향, 태도, 습관 추론
        user_profile = infer_user_profile(row, finance_trends, conversation_history, user_msg, emotion_data)
        
        # ── 상품 추천 필요 여부 확인 ────────────────────────────── #
        needs_product_recommendation = False
        product_type = None
        
        # 대화 내용에서 상품 관련 키워드 확인
        product_keywords = {
            "예금": PRODUCT_TYPE_DEPOSIT,
            "적금": PRODUCT_TYPE_DEPOSIT,
            "정기예금": PRODUCT_TYPE_DEPOSIT,
            "입출금": PRODUCT_TYPE_DEPOSIT,
            "이자율": PRODUCT_TYPE_DEPOSIT,
            "금리": PRODUCT_TYPE_DEPOSIT,
            "펀드": PRODUCT_TYPE_FUND,
            "투자": PRODUCT_TYPE_FUND,
            "수익률": PRODUCT_TYPE_FUND,
            "주식형": PRODUCT_TYPE_FUND,
            "채권형": PRODUCT_TYPE_FUND,
            "상품": None,  # 일반적인 상품 언급
            "추천": None,  # 추천 요청
        }
        
        for keyword, ptype in product_keywords.items():
            if keyword in user_msg:
                needs_product_recommendation = True
                if ptype:  # 특정 상품 타입이 있는 경우
                    product_type = ptype
                break
        
        # ── GPT로 맞춤형 조언 생성을 위한 프롬프트 구성 ────────────────── #
        sys_prompt = build_finance_chat_prompt(row, finance_trends, user_profile, label)
        
        # 사용자 재무 데이터, 대화 히스토리, 질문을 함께 전달하여 맞춤형 조언 요청
        user_content = f"""[사용자 재무 데이터]
{user_finance_summary}

[사용자 성향 프로필]
{user_profile}

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
                max_tokens=800,
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

        # 상품 추천이 필요한 경우 상품 추천 정보 추가
        if needs_product_recommendation:
            try:
                products = await recommend_products(
                    user_id, 
                    user_finance_summary, 
                    emotion_data,
                    product_type,
                    limit=3
                )
                
                if products:
                    # 상품 추천 결과가 있으면 원래 응답에 추가
                    recommendation_type = product_type if product_type else (
                        PRODUCT_TYPE_DEPOSIT if "적금" in user_msg or "예금" in user_msg else PRODUCT_TYPE_FUND
                    )
                    product_reply = format_product_recommendation(products, recommendation_type, emotion_data)
                    
                    # 원래 응답과 상품 추천 합치기
                    combined_reply = f"{reply}\n\n{product_reply}"
                    reply = combined_reply
            except Exception as e:
                logger.error(f"상품 추천 처리 중 오류 발생: {str(e)}")
                # 상품 추천 실패 시에도 기본 응답은 제공

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


# ───────────────────── 1. 개인화된 재무 캐릭터 모델 도입 ───────────────────── #
def infer_user_profile(row: Dict, finance_trends: Dict, conversation_history: str, user_msg: str, emotion_data: Dict = None) -> Dict:
    """
    사용자 재무 데이터를 바탕으로 재무 성향 추론
    
    Parameters:
    -----------
    row : dict
        사용자의 재무 관련 데이터
    finance_trends : dict
        재무 트렌드 분석 결과
    conversation_history : str
        이전 대화 내용
    user_msg : str
        현재 사용자 메시지
    emotion_data : dict
        감정 분석 결과
        
    Returns:
    --------
    dict
        추론된 사용자 프로필
    """
    profile = {}
    
    # 재무성향 추론
    if row.get("liquidity_score", 50) > 70 and finance_trends.get("balance_trend") == "지속 증가":
        profile["재무성향"] = "보수적 소비자"
    elif row.get("card_usage_b0m", 0) > row.get("avg_card_usage_3m", 0) * 1.2:
        profile["재무성향"] = "과소비 경향 있음"
    elif finance_trends.get("financial_health") == "주의 필요":
        profile["재무성향"] = "위험 감수 소비자"
    elif row.get("investment_ratio", 0) > 50:
        profile["재무성향"] = "위험 선호 투자자"
    else:
        profile["재무성향"] = "일반적 소비자"
        
    # 금융단계 추론
    age = row.get("age", 35)
    if age < 30:
        profile["금융단계"] = "사회초년생"
    elif 30 <= age < 45:
        profile["금융단계"] = "자산형성기"
    elif 45 <= age < 55:
        profile["금융단계"] = "자녀양육기"
    else:
        profile["금융단계"] = "은퇴준비기"
        
    # 스트레스 반응 추론 (감정 분석 결과 활용)
    if emotion_data:
        # 기본 감정 매핑 정의
        emotion_mapping = {
            "화남": "anger",
            "혐오": "disgust", 
            "공포": "fear",
            "행복": "happiness",
            "중립": "neutral",
            "슬픔": "sadness",
            "놀람": "surprise",
            "걱정": "anxiety"  # 추가 감정
        }
        
        # 지정된 감정 상태 사용
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        
        # 스트레스 반응 정의
        if dominant_emotion == "화남":
            profile["스트레스 반응"] = "금융 문제에 대한 분노감 표출"
        elif dominant_emotion == "슬픔":
            profile["스트레스 반응"] = "금융 문제에 대한 좌절감 표출"
        elif dominant_emotion == "공포" or dominant_emotion == "걱정":
            profile["스트레스 반응"] = "금융에 대한 불안증 높음"
        elif emotion_data.get("is_anxious", False):
            profile["스트레스 반응"] = "감정적 불안감이 높은 상태"
        else:
            profile["스트레스 반응"] = "스스로 해결하려는 성향"
        
        # 감정 상태 추가
        profile["감정 상태"] = dominant_emotion
        profile["감정 강도"] = "강함" if emotion_data.get("dominant_score", 0) > 0.7 else "보통"
    
    return profile


# ───────────────────── 재무 상담 프롬프트 구성 함수 ───────────────────── #
def build_finance_chat_prompt(row: Dict, finance_trends: Dict, user_profile: Dict, label: str) -> str:
    """
    사용자 재무 데이터 및 메시지를 바탕으로 재무 상담 프롬프트 생성
    
    Parameters:
    -----------
    row : dict
        사용자의 재무 관련 데이터
    finance_trends : dict
        재무 트렌드 분석 결과
    user_profile : dict
        추론된 사용자 성향 정보
    label : str
        시나리오 라벨
        
    Returns:
    --------
    str
        GPT 프롬프트
    """
    # 기본 시스템 프롬프트 설정
    sys_prompt = (
        "너는 전문 재무 상담 챗봇이야. 사용자의 재무 데이터, 대화 맥락, 질문을 종합적으로 분석해서 구체적이고 실용적인 맞춤형 조언을 제공해야 해. "
        "답변은 반드시 비교적 짧게(최대 100자 이내) 작성하고, 친근한 한국어로 1~2문장만 작성해. 숫자는 % 대신 '퍼센트' 표기, 어려운 금융 용어는 풀어서 설명해. "
        "사용자의 최근 대화 내용과 재무 트렌드를 고려하여 일관성 있고 짧지만 핵심적인 조언을 제공해."
    )
    
    # 3. 핵심 지표 강조 유도
    sys_prompt += """

특히 아래 주요 지표가 변화했을 경우, 조언에서 우선적으로 반영해줘:
- 최근 연체 발생 여부
- 잔액 급감 또는 카드사용 급증
- 유동성 점수 40 이하
"""
    
    # 5. 긴급/위험 상태 경고 강화
    if row.get("is_delinquent", 0) or finance_trends.get("stress_index", 0) > 80:
        sys_prompt += """

사용자의 재무 상태가 위험하니, 반드시 신중하고 경고성 있는 조언을 해줘.
"""
    
    # 8. 시나리오 충돌 또는 다중 시나리오 대응
    sys_prompt += """

복수의 재무 문제가 감지되면 가장 시급한 문제부터 조언을 제공해. 예: 연체 > 잔액 감소 > 과소비
"""
    
    # 12. 상담 타입 분기 (정보형 vs 행동형 vs 감정형)
    sys_prompt += """

사용자의 말투와 감정 상태에 따라, 정보형/행동형/공감형 조언 중 가장 적절한 스타일로 말해줘.
- 정보형: "○○란 이런 것이고, 이렇게 관리해야 해요."
- 행동형: "○○을 꼭 확인하거나 ○○를 신청해보세요."
- 감정형: "요즘 참 힘드셨죠. 조심스레 추천드리면..."

특히 다음 감정 상태에 따라 상담 스타일을 조정해야 합니다:
- 슬픔/걱정 감정일 경우: 공감형 접근을 우선하고, 희망적 메시지 포함
- 화남 감정일 경우: 객관적 정보 제공 후 실질적 해결책 제시
- 중립 감정일 경우: 정보형 접근 우선
- 행복 감정일 경우: 긍정적 피드백과 함께 미래 계획 논의
"""
    
    return sys_prompt