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

# ───────────────────── 재무 트렌드 분석 함수 ───────────────────── #
def analyze_financial_trends(row: dict) -> dict:
    """사용자 재무 데이터의 트렌드를 분석하고 요약하는 함수
    
    다양한 시점의 데이터를 비교하여 변화 트렌드를 파악합니다.
    """
    trends = {}
    
    try:
        # 1. 잔액 추세 분석
        if all(key in row for key in ["balance_b0m", "balance_b1m", "balance_b2m"]):
            # 최근 3개월 동안의 잔액 변화
            b0 = row["balance_b0m"]
            b1 = row["balance_b1m"]
            b2 = row["balance_b2m"]
            
            # 잔액 변화율 계산 (%)
            if b1 > 0:
                change_1m = ((b0 - b1) / b1) * 100
            else:
                change_1m = 0
                
            if b2 > 0:
                change_2m = ((b0 - b2) / b2) * 100
            else:
                change_2m = 0
            
            # 추세 파악 및 저장
            if change_1m > 5 and change_2m > 0:  # 지속적 잔액 증가
                trends["balance_trend"] = "지속 증가"
            elif change_1m < -5 and change_2m < 0:  # 지속적 잔액 감소
                trends["balance_trend"] = "지속 감소"
            elif abs(change_1m) < 3:  # 안정적
                trends["balance_trend"] = "안정적"
            else:
                trends["balance_trend"] = "변동성 있음"
        
        # 2. 카드 사용 패턴 분석
        if all(key in row for key in ["card_usage_b0m", "card_usage_b1m", "card_usage_b2m"]):
            # 최근 3개월 동안의 카드 사용량 변화
            c0 = row["card_usage_b0m"]
            c1 = row["card_usage_b1m"] 
            c2 = row["card_usage_b2m"]
            
            # 평균 계산
            avg = (c0 + c1 + c2) / 3
            
            # 추세 파악
            if c0 > c1 and c1 > c2 and c0 > avg * 1.1:  # 지속 증가 추세
                trends["card_trend"] = "증가 추세"
            elif c0 < c1 and c1 < c2 and c0 < avg * 0.9:  # 지속 감소 추세
                trends["card_trend"] = "감소 추세"
            elif abs(c0 - avg) < avg * 0.1:  # 안정적
                trends["card_trend"] = "안정적"
            else:
                trends["card_trend"] = "불규칙"
        
        # 3. 잔액 vs 카드 사용 관계 분석
        if all(key in row for key in ["balance_b0m", "card_usage_b0m", "avg_balance_3m", "avg_card_usage_3m"]):
            bal_ratio = row["balance_b0m"] / (row["avg_balance_3m"] + 0.001)
            card_ratio = row["card_usage_b0m"] / (row["avg_card_usage_3m"] + 0.001)
            
            # 현재 상황 해석
            if bal_ratio < 0.7 and card_ratio > 1.2:  # 잔액 낮고 지출 높음
                trends["financial_health"] = "주의 필요"
            elif bal_ratio > 1.2 and card_ratio < 0.8:  # 잔액 높고 지출 낮음
                trends["financial_health"] = "양호한 상태"
            elif bal_ratio > 1.0 and card_ratio > 1.0:  # 잔액과 지출 모두 증가
                trends["financial_health"] = "소득 증가 가능성"
            else:
                trends["financial_health"] = "일반적"
    except Exception as e:
        logger.warning(f"재무 트렌드 분석 중 오류: {str(e)}")
        
    return trends

# ──────────────────── DB 조회 함수 ──────────────────── #
async def _get_user_metrics(user_id: str) -> dict[str, Any] | None:
    """여러 테이블에서 사용자 데이터 조회 → 통합 dict
    
    부분 데이터 처리: 사용자 기본 정보만 있어도 서비스를 제공하며, 테이블별로 데이터가 없는 경우
    기본값을 사용하여 최대한 정보를 제공합니다.
    """
    try:
        async with SessionMaker() as sess:
            # 사용자 정보 조회 (필수)
            user_query = select(User).where(User.user_id == user_id)
            user_row = (await sess.execute(user_query)).scalar_one_or_none()
            
            if not user_row:
                logger.warning(f"사용자 {user_id} 기본 정보가 없습니다.")
                return None
                
            # 각 테이블에서 최근 데이터 조회를 위한 서브쿼리 정의
            # 데이터가 없더라도 오류를 발생시키지 않음
            queries = {
                "card": select(CardUsage).where(
                    CardUsage.user_id == user_id
                ).order_by(CardUsage.record_date.desc()).limit(1),
                
                "delinquency": select(Delinquency).where(
                    Delinquency.user_id == user_id
                ).order_by(Delinquency.record_date.desc()).limit(1),
                
                "balance": select(BalanceInfo).where(
                    BalanceInfo.user_id == user_id
                ).order_by(BalanceInfo.record_date.desc()).limit(1),
                
                "spending": select(SpendingPattern).where(
                    SpendingPattern.user_id == user_id
                ).order_by(SpendingPattern.record_date.desc()).limit(1),
                
                "scenario": select(ScenarioLabel).where(
                    ScenarioLabel.user_id == user_id
                ).order_by(ScenarioLabel.record_date.desc()).limit(1)
            }
            
            # 통합 딕셔너리 생성 - 기본값은 사용자 데이터
            result = {}
            for key, value in user_row.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value
            
            # 각 테이블 데이터 조회 및 설정
            # 각 테이블의 중요도에 따라 필수/선택 지정
            has_critical_data = True
            missing_tables = []
            
            # 1. 중요 테이블 - 없어도 서비스는 제공하지만 기본값으로 대체
            critical_tables = ["card", "balance"]  # 중요 테이블
            
            for table_name in critical_tables:
                query = queries[table_name]
                row = (await sess.execute(query)).scalar_one_or_none()
                
                if not row:
                    missing_tables.append(table_name)
                    # 테이블별 기본값 설정
                    if table_name == "card":
                        result["card_usage_b0m"] = 0.0
                        result["card_usage_b1m"] = 0.0
                        result["card_usage_b2m"] = 0.0
                        result["avg_card_usage_3m"] = 0.0
                        result["card_usage_trend"] = 0.0
                        logger.info(f"사용자 {user_id}의 카드 사용 데이터 없음, 기본값 사용")
                    elif table_name == "balance":
                        result["balance_b0m"] = 10000.0  # 기본 잔액
                        result["balance_b1m"] = 10000.0
                        result["balance_b2m"] = 10000.0
                        result["avg_balance_3m"] = 10000.0
                        result["balance_trend"] = 0.0
                        logger.info(f"사용자 {user_id}의 잔액 데이터 없음, 기본값 사용")
                    continue
                    
                # 데이터 있는 경우 추가
                for key, value in row.__dict__.items():
                    if not key.startswith('_') and key != 'user_id' and key != 'record_date':
                        result[key] = value
            
            # 중요 데이터가 없어도 계속 진행 - 기본값으로 대체하여 서비스 제공
            if missing_tables:
                logger.warning(f"사용자 {user_id}의 일부 중요 테이블 데이터 없음: {', '.join(missing_tables)}")
            
            # 2. 선택적 테이블 - 있으면 사용, 없어도 기본 기능 사용 가능
            optional_tables = ["delinquency", "spending", "scenario"]
            
            for table_name in optional_tables:
                query = queries[table_name]
                row = (await sess.execute(query)).scalar_one_or_none()
                
                if not row:
                    logger.info(f"사용자 {user_id}의 {table_name} 데이터 없음, 기본값 사용")
                    # 테이블별 기본값 설정
                    if table_name == "delinquency":
                        result["is_delinquent"] = 0
                        result["delinquent_balance_b0m"] = 0.0
                        result["recent_delinquent_days"] = 0
                    elif table_name == "spending":
                        result["spending_shopping"] = 0.0
                        result["spending_food"] = 0.0
                        result["card_application_count"] = 0
                    elif table_name == "scenario":
                        result["scenario_labels"] = "no_issue"
                    continue
                
                # 데이터 있는 경우 추가
                for key, value in row.__dict__.items():
                    if not key.startswith('_') and key != 'user_id' and key != 'record_date':
                        result[key] = value
            
            # 3. 계산된 필드 추가 (scenario_engine에서 필요한 가상 필드)
            # 예시: 메타데이터 필드 등을 추가할 수 있음
            result["revolving_count_3m"] = result.get("revolving_count_3m", 0)  # 기본값
            result["stress_index"] = result.get("stress_index", 50.0)  # 기본값
            
            # 3-1. 중요 필드 확인 및 기본값 설정 (시나리오 엔진에 필요한 필드들)
            essential_fields = [
                "gender", "age", "income_level", "job_type", "financial_products"
            ]
            
            for field in essential_fields:
                if field not in result or result[field] is None:
                    if field == "gender":
                        result[field] = "unknown"
                    elif field == "age":
                        result[field] = 35
                    elif field == "income_level":
                        result[field] = "middle"
                    elif field == "job_type":
                        result[field] = "office_worker"
                    elif field == "financial_products":
                        result[field] = "deposit,loan"
                    logger.info(f"사용자 {user_id}의 {field} 정보 없음, 기본값 설정")
            
            # 3-2. 분석에 필요한 추가 계산 필드 처리
            try:
                balance_ratio = result["balance_b0m"] / (result["avg_balance_3m"] + 0.001)
                result["liquidity_score"] = min(100, max(0, 100 - (balance_ratio * 20)))
            except KeyError:
                result["liquidity_score"] = 50.0  # 키가 없는 경우 기본값
            except ZeroDivisionError:
                result["liquidity_score"] = 50.0  # 나눗셈 오류 시 기본값
            except Exception as e:
                logger.warning(f"유동성 점수 계산 중 오류: {str(e)}")
                result["liquidity_score"] = 50.0  # 기타 오류 시 기본값
                
            return result
            
    except Exception as e:
        # 테이블 없거나 DB 오류 발생 시 로그만 출력하고 None 반환
        if "Table 'emofinance." in str(e):
            logger.warning(f"테이블이 없습니다: {str(e)}. 데이터베이스 확인 필요.")
        else:
            logger.error(f"DB 조회 오류: {str(e)}")
        return None

# ───────────────────── 메인 엔드포인트 로직 ───────────────────── #
@backoff.on_exception(backoff.expo, RETRY_ERRORS, max_tries=3)
async def get_finance_reply(user_id: str, user_msg: str) -> Tuple[str, Optional[Dict]]:
    """
    1️⃣ 사용자 지표(DB에서 조회)  
    2️⃣ 시나리오 스코어링 + 템플릿 조언  
    3️⃣ GPT-3.5로 톤·길이 다듬기
    """
    try:
        # 사용자 지표 조회
        row = await _get_user_metrics(user_id)
        if not row:
            # 지표가 없는 신규/테스트 계정 → 일반 채팅으로 폴백
            logger.warning(f"사용자 {user_id} 지표 없음. 일반 채팅으로 응답")
            from app.services.generic_chat import get_generic_reply
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
            # 프롬프트 오류 시 템플릿 그대로 사용
            logger.error(f"OpenAI API 오류: {str(e)}")
            # 기본 응답 제공
            reply = f"재무 상태 '{label}'에 맞는 조언을 드리려 했으나 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        except Exception as e:
            # 기타 오류 시에도 템플릿 그대로 사용
            logger.error(f"OpenAI API 호출 오류: {str(e)}")
            # 기본 응답 제공
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
        from app.services.generic_chat import get_generic_reply
        reply = await get_generic_reply(user_id, user_msg)
        return reply, None
