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
    """여러 테이블에서 사용자 데이터 조회 → 통합 dict"""
    try:
        async with SessionMaker() as sess:
            # 사용자 정보 조회
            user_query = select(User).where(User.user_id == user_id)
            user_row = (await sess.execute(user_query)).scalar_one_or_none()
            
            if not user_row:
                return None
                
            # 가장 최근 날짜의 데이터 조회를 위한 서브쿼리
            card_query = select(CardUsage).where(
                CardUsage.user_id == user_id
            ).order_by(CardUsage.record_date.desc()).limit(1)
            
            delinquency_query = select(Delinquency).where(
                Delinquency.user_id == user_id
            ).order_by(Delinquency.record_date.desc()).limit(1)
            
            balance_query = select(BalanceInfo).where(
                BalanceInfo.user_id == user_id
            ).order_by(BalanceInfo.record_date.desc()).limit(1)
            
            spending_query = select(SpendingPattern).where(
                SpendingPattern.user_id == user_id
            ).order_by(SpendingPattern.record_date.desc()).limit(1)
            
            scenario_query = select(ScenarioLabel).where(
                ScenarioLabel.user_id == user_id
            ).order_by(ScenarioLabel.record_date.desc()).limit(1)
            
            # 각 테이블에서 최근 데이터 조회
            card_row = (await sess.execute(card_query)).scalar_one_or_none()
            delinquency_row = (await sess.execute(delinquency_query)).scalar_one_or_none()
            balance_row = (await sess.execute(balance_query)).scalar_one_or_none()
            spending_row = (await sess.execute(spending_query)).scalar_one_or_none()
            scenario_row = (await sess.execute(scenario_query)).scalar_one_or_none()
            
            # 모든 데이터가 없는 경우
            if not card_row or not delinquency_row or not balance_row or not spending_row or not scenario_row:
                logger.warning(f"사용자 {user_id}의 일부 테이블 데이터가 없습니다.")
                # 부분 데이터가 있는 경우 처리 가능하도록 할 수도 있음
                return None
            
            # 통합 딕셔너리 생성
            result = {}
            
            # User 테이블 데이터 추가
            for key, value in user_row.__dict__.items():
                if not key.startswith('_'):
                    result[key] = value
                    
            # 다른 테이블의 데이터 추가
            for row in [card_row, delinquency_row, balance_row, spending_row, scenario_row]:
                for key, value in row.__dict__.items():
                    if not key.startswith('_') and key != 'user_id' and key != 'record_date':
                        result[key] = value
            
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
