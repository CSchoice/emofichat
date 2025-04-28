from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select

from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel
from sqlalchemy import select, desc

# 로거 설정
logger = logging.getLogger(__name__)

async def get_user_metrics(user_id: str) -> Optional[Dict[str, Any]]:
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

            card_rows = (
                await sess.execute(
                    select(CardUsage)
                    .where(CardUsage.user_id == user_id)
                    .order_by(desc(CardUsage.record_date))
                    .limit(2)
                )
            ).scalars().all()

            # 2) 현월·전월 총결제액 계산
            if len(card_rows) >= 2:
                cur, prev = card_rows[0], card_rows[1]
                cur_total = float(cur.credit_usage_3m or 0) + float(cur.check_usage_3m or 0)
                prev_total = float(prev.credit_usage_3m or 0) + float(prev.check_usage_3m or 0)
            elif len(card_rows) == 1:
                cur = card_rows[0]
                cur_total = float(cur.credit_usage_3m or 0) + float(cur.check_usage_3m or 0)
                prev_total = 0.0
            else:
                cur_total = prev_total = 0.0

            result["total_payment_amount"] = cur_total
            result["total_payment_amount_전월"] = prev_total
            
            # 각 테이블 데이터 조회 및 설정
            # 각 테이블의 중요도에 따라 필수/선택 지정
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
                # decimal과 float 간 연산 오류 해결을 위해 형변환 처리 추가
                balance_b0m = float(result["balance_b0m"]) if result["balance_b0m"] is not None else 0.0
                avg_balance_3m = float(result["avg_balance_3m"]) if result["avg_balance_3m"] is not None else 0.001
                balance_ratio = balance_b0m / (avg_balance_3m + 0.001)  # 0 나눗셈 방지를 위해 0.001 추가
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
