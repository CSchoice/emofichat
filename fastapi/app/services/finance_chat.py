from __future__ import annotations

import backoff
from typing import Dict, Any, Tuple, Optional
import logging

from openai import (
    APITimeoutError, APIConnectionError, RateLimitError, BadRequestError
)
from sqlalchemy import select

from app.core.openai_client import client as openai_client
from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel
from app.services.scenario_engine import score_scenarios
from app.services.advice_templates import TEMPLATES
from app.services.generic_chat import load_history, save_history

# 로거 설정
logger = logging.getLogger(__name__)

# ───────────────────── 공통 설정 ────────────────────── #
RETRY_ERRORS = (APITimeoutError, APIConnectionError, RateLimitError)

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
        # 시나리오가 존재하지 않으면 no_issue 기본값 사용
        advice = TEMPLATES.get(label, TEMPLATES.get("no_issue", "도와드릴 점이 없습니다."))

        # ── GPT 다듬기 ─────────────────────────────────────────── #
        sys_prompt = (
            "너는 재무 상담 챗봇이야. 답변은 친근한 한국어 2~3문장, "
            "숫자는 % 대신 '퍼센트' 표기, 어려운 금융 용어는 풀어서 설명해."
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"[사용자]\n{user_msg}"},
            {"role": "assistant", "content": advice},           # 초안
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
            reply = advice
        except Exception as e:
            # 기타 오류 시에도 템플릿 그대로 사용
            logger.error(f"OpenAI API 호출 오류: {str(e)}")
            reply = advice

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
