from __future__ import annotations

import logging
import decimal
from typing import Dict, Any, Optional
from sqlalchemy import select, desc

from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel

# 로거 설정
logger = logging.getLogger(__name__)

def safe_value(value: Any) -> Any:
    """Decimal 타입을 float으로 변환 (기타 타입은 그대로 반환)"""
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value

async def get_user_metrics(user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 관련 주요 데이터 통합 조회 (Decimal safe 처리)"""
    try:
        async with SessionMaker() as sess:
            # 1. 사용자 기본 정보 조회
            user_row = (await sess.execute(
                select(User).where(User.user_id == user_id)
            )).scalar_one_or_none()

            if not user_row:
                logger.warning(f"[get_user_metrics] 사용자 {user_id} 기본 정보 없음")
                return None

            result = {
                key: safe_value(value)
                for key, value in user_row.__dict__.items()
                if not key.startswith('_')
            }

            # 2. 카드 사용 이력 조회 (최근 2개월)
            card_rows = (await sess.execute(
                select(CardUsage)
                .where(CardUsage.user_id == user_id)
                .order_by(desc(CardUsage.record_date))
                .limit(2)
            )).scalars().all()

            if card_rows:
                cur_total = float(card_rows[0].credit_usage_3m or 0) + float(card_rows[0].check_usage_3m or 0)
                prev_total = (
                    float(card_rows[1].credit_usage_3m or 0) + float(card_rows[1].check_usage_3m or 0)
                    if len(card_rows) > 1 else 0.0
                )
            else:
                cur_total = prev_total = 0.0

            result["total_payment_amount"] = cur_total
            result["total_payment_amount_전월"] = prev_total

            # 3. 중요 + 선택 테이블 조회
            queries = {
                "card": select(CardUsage).where(CardUsage.user_id == user_id).order_by(desc(CardUsage.record_date)).limit(1),
                "balance": select(BalanceInfo).where(BalanceInfo.user_id == user_id).order_by(desc(BalanceInfo.record_date)).limit(1),
                "delinquency": select(Delinquency).where(Delinquency.user_id == user_id).order_by(desc(Delinquency.record_date)).limit(1),
                "spending": select(SpendingPattern).where(SpendingPattern.user_id == user_id).order_by(desc(SpendingPattern.record_date)).limit(1),
                "scenario": select(ScenarioLabel).where(ScenarioLabel.user_id == user_id).order_by(desc(ScenarioLabel.record_date)).limit(1),
            }

            critical_tables = ["card", "balance"]
            optional_tables = ["delinquency", "spending", "scenario"]

            missing_critical = []

            # 3-1. 중요 테이블 조회
            for table in critical_tables:
                row = (await sess.execute(queries[table])).scalar_one_or_none()
                if not row:
                    missing_critical.append(table)
                    if table == "card":
                        result.update({
                            "card_usage_b0m": 0.0,
                            "card_usage_b1m": 0.0,
                            "card_usage_b2m": 0.0,
                            "avg_card_usage_3m": 0.0,
                            "card_usage_trend": 0.0,
                        })
                    elif table == "balance":
                        result.update({
                            "balance_b0m": 10000.0,
                            "balance_b1m": 10000.0,
                            "balance_b2m": 10000.0,
                            "avg_balance_3m": 10000.0,
                            "balance_trend": 0.0,
                        })
                    logger.info(f"[get_user_metrics] 사용자 {user_id}의 {table} 데이터 없음, 기본값 대입")
                else:
                    result.update({
                        key: safe_value(value)
                        for key, value in row.__dict__.items()
                        if not key.startswith('_') and key not in ("user_id", "record_date")
                    })

            if missing_critical:
                logger.warning(f"[get_user_metrics] 사용자 {user_id} 중요 테이블 일부 누락: {', '.join(missing_critical)}")

            # 3-2. 선택 테이블 조회
            for table in optional_tables:
                row = (await sess.execute(queries[table])).scalar_one_or_none()
                if not row:
                    logger.info(f"[get_user_metrics] 사용자 {user_id}의 {table} 데이터 없음, 기본값 대입")
                    if table == "delinquency":
                        result.update({
                            "is_delinquent": 0,
                            "delinquent_balance_b0m": 0.0,
                            "recent_delinquent_days": 0,
                        })
                    elif table == "spending":
                        result.update({
                            "spending_shopping": 0.0,
                            "spending_food": 0.0,
                            "card_application_count": 0,
                        })
                    elif table == "scenario":
                        result["scenario_labels"] = "no_issue"
                else:
                    result.update({
                        key: safe_value(value)
                        for key, value in row.__dict__.items()
                        if not key.startswith('_') and key not in ("user_id", "record_date")
                    })

            # 4. 필수 메타 필드 보완
            essential_defaults = {
                "gender": "unknown",
                "age": 35,
                "income_level": "middle",
                "job_type": "office_worker",
                "financial_products": "deposit,loan",
            }
            for field, default_value in essential_defaults.items():
                if field not in result or result[field] is None:
                    result[field] = default_value
                    logger.info(f"[get_user_metrics] 사용자 {user_id}의 {field} 없음, 기본값 설정")

            # 5. 추가 계산 필드
            try:
                balance_b0m = float(result.get("balance_b0m", 0.0))
                avg_balance_3m = float(result.get("avg_balance_3m", 0.001))
                balance_ratio = balance_b0m / (avg_balance_3m + 0.001)
                result["liquidity_score"] = min(100, max(0, 100 - (balance_ratio * 20)))
            except Exception as e:
                logger.warning(f"[get_user_metrics] 유동성 점수 계산 오류: {e}")
                result["liquidity_score"] = 50.0

            # 6. 가상 필드 기본값
            result.setdefault("revolving_count_3m", 0)
            result.setdefault("stress_index", 50.0)

            return result

    except Exception as e:
        logger.error(f"[get_user_metrics] DB 조회 오류: {e}")
        return None
