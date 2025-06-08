"""
사용자 금융 정보 서비스

사용자의 금융 데이터를 조회하고 분석하는 서비스
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.core.db import SessionMaker
from app.models.financial_data import (
    User, BalanceInfo, CardUsage, Delinquency, ScenarioLabel, SpendingPattern
)

logger = logging.getLogger(__name__)


class UserFinancialService:
    """사용자 금융 정보 서비스 클래스"""
    
    async def get_db_session(self) -> AsyncSession:
        """데이터베이스 세션 가져오기"""
        return SessionMaker()
    
    async def get_user_basic_info(self, user_id: str) -> Dict[str, Any]:
        """사용자 기본 정보 조회"""
        async with await self.get_db_session() as session:
            user_result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = user_result.scalars().first()
            
            if not user:
                return {"error": "사용자를 찾을 수 없습니다."}
            
            return {
                "user_id": user.user_id,
                "gender": user.gender,
                "age": user.age,
                "residence": user.residence,
                "workplace": user.workplace,
                "marketing_agree": user.marketing_agree
            }
    
    async def get_balance_info(self, user_id: str) -> Dict[str, Any]:
        """사용자 잔액 정보 조회"""
        async with await self.get_db_session() as session:
            balance_result = await session.execute(
                select(BalanceInfo)
                .where(BalanceInfo.user_id == user_id)
                .order_by(desc(BalanceInfo.record_date))
                .limit(1)
            )
            balance = balance_result.scalars().first()
            
            if not balance:
                return {"error": "잔액 정보를 찾을 수 없습니다."}
            
            return {
                "record_date": balance.record_date,
                "balance": float(balance.balance_b0m) if balance.balance_b0m else 0,
                "balance_lump": float(balance.balance_lump_b0m) if balance.balance_lump_b0m else 0,
                "balance_loan": float(balance.balance_loan_b0m) if balance.balance_loan_b0m else 0,
                "avg_balance_3m": float(balance.avg_balance_3m) if balance.avg_balance_3m else 0,
                "avg_ca_balance_3m": float(balance.avg_ca_balance_3m) if balance.avg_ca_balance_3m else 0,
                "avg_loan_balance_3m": float(balance.avg_loan_balance_3m) if balance.avg_loan_balance_3m else 0,
                "ca_interest_rate": float(balance.ca_interest_rate) if balance.ca_interest_rate else 0,
                "revolving_min_payment_ratio": float(balance.revolving_min_payment_ratio) if balance.revolving_min_payment_ratio else 0
            }
    
    async def get_card_usage(self, user_id: str) -> Dict[str, Any]:
        """사용자 카드 사용 정보 조회"""
        async with await self.get_db_session() as session:
            card_result = await session.execute(
                select(CardUsage)
                .where(CardUsage.user_id == user_id)
                .order_by(desc(CardUsage.record_date))
                .limit(1)
            )
            card = card_result.scalars().first()
            
            if not card:
                return {"error": "카드 사용 정보를 찾을 수 없습니다."}
            
            return {
                "record_date": card.record_date,
                "credit_card_count": card.credit_card_count,
                "check_card_count": card.check_card_count,
                "credit_usage_3m": float(card.credit_usage_3m) if card.credit_usage_3m else 0,
                "check_usage_3m": float(card.check_usage_3m) if card.check_usage_3m else 0,
                "top1_card_usage": float(card.top1_card_usage) if card.top1_card_usage else 0,
                "top2_card_usage": float(card.top2_card_usage) if card.top2_card_usage else 0,
                "first_limit_amount": float(card.first_limit_amount) if card.first_limit_amount else 0,
                "current_limit_amount": float(card.current_limit_amount) if card.current_limit_amount else 0,
                "ca_limit_amount": float(card.ca_limit_amount) if card.ca_limit_amount else 0
            }
    
    async def get_delinquency_info(self, user_id: str) -> Dict[str, Any]:
        """사용자 연체 정보 조회"""
        async with await self.get_db_session() as session:
            delinquency_result = await session.execute(
                select(Delinquency)
                .where(Delinquency.user_id == user_id)
                .order_by(desc(Delinquency.record_date))
                .limit(1)
            )
            delinquency = delinquency_result.scalars().first()
            
            if not delinquency:
                return {"error": "연체 정보를 찾을 수 없습니다."}
            
            return {
                "record_date": delinquency.record_date,
                "delinquent_balance": float(delinquency.delinquent_balance_b0m) if delinquency.delinquent_balance_b0m else 0,
                "delinquent_balance_ca": float(delinquency.delinquent_balance_ca_b0m) if delinquency.delinquent_balance_ca_b0m else 0,
                "recent_delinquent_days": delinquency.recent_delinquent_days,
                "max_delinquent_months": delinquency.max_delinquent_months_r15m,
                "is_delinquent": delinquency.is_delinquent,
                "limit_down_amount": float(delinquency.limit_down_amount_r12m) if delinquency.limit_down_amount_r12m else 0,
                "limit_up_amount": float(delinquency.limit_up_amount_r12m) if delinquency.limit_up_amount_r12m else 0,
                "limit_up_available": float(delinquency.limit_up_available) if delinquency.limit_up_available else 0
            }
    
    async def get_scenario_label(self, user_id: str) -> Dict[str, Any]:
        """사용자 시나리오 라벨 조회"""
        async with await self.get_db_session() as session:
            scenario_result = await session.execute(
                select(ScenarioLabel)
                .where(ScenarioLabel.user_id == user_id)
                .order_by(desc(ScenarioLabel.record_date))
                .limit(1)
            )
            scenario = scenario_result.scalars().first()
            
            if not scenario:
                return {"error": "시나리오 라벨을 찾을 수 없습니다."}
            
            return {
                "record_date": scenario.record_date,
                "scenario_labels": scenario.scenario_labels,
                "dti_estimate": float(scenario.dti_estimate) if scenario.dti_estimate else 0,
                "spending_change_ratio": float(scenario.spending_change_ratio) if scenario.spending_change_ratio else 0,
                "essential_ratio": float(scenario.essential_ratio) if scenario.essential_ratio else 0,
                "credit_usage_ratio": float(scenario.credit_usage_ratio) if scenario.credit_usage_ratio else 0,
                "debt_ratio": float(scenario.debt_ratio) if scenario.debt_ratio else 0,
                "revolving_dependency": float(scenario.revolving_dependency) if scenario.revolving_dependency else 0,
                "necessity_ratio": float(scenario.necessity_ratio) if scenario.necessity_ratio else 0,
                "housing_ratio": float(scenario.housing_ratio) if scenario.housing_ratio else 0,
                "medical_ratio": float(scenario.medical_ratio) if scenario.medical_ratio else 0
            }
    
    async def get_spending_pattern(self, user_id: str) -> Dict[str, Any]:
        """사용자 지출 패턴 조회"""
        async with await self.get_db_session() as session:
            spending_result = await session.execute(
                select(SpendingPattern)
                .where(SpendingPattern.user_id == user_id)
                .order_by(desc(SpendingPattern.record_date))
                .limit(1)
            )
            spending = spending_result.scalars().first()
            
            if not spending:
                return {"error": "지출 패턴을 찾을 수 없습니다."}
            
            return {
                "record_date": spending.record_date,
                "spending_shopping": float(spending.spending_shopping) if spending.spending_shopping else 0,
                "spending_food": float(spending.spending_food) if spending.spending_food else 0,
                "spending_transport": float(spending.spending_transport) if spending.spending_transport else 0,
                "spending_medical": float(spending.spending_medical) if spending.spending_medical else 0,
                "spending_payment": float(spending.spending_payment) if spending.spending_payment else 0,
                "life_stage": spending.life_stage,
                "card_application_count": spending.card_application_count,
                "last_card_issued_months_ago": spending.last_card_issued_months_ago
            }
    
    async def get_user_financial_summary(self, user_id: str) -> Dict[str, Any]:
        """사용자 금융 정보 종합 요약"""
        result = {}
        
        # 사용자 기본 정보
        user_info = await self.get_user_basic_info(user_id)
        if "error" in user_info:
            return {"error": "사용자를 찾을 수 없습니다."}
        
        result["user"] = user_info
        
        # 잔액 정보
        balance_info = await self.get_balance_info(user_id)
        if "error" not in balance_info:
            result["balance"] = balance_info
        
        # 카드 사용 정보
        card_usage = await self.get_card_usage(user_id)
        if "error" not in card_usage:
            result["card_usage"] = card_usage
        
        # 연체 정보
        delinquency_info = await self.get_delinquency_info(user_id)
        if "error" not in delinquency_info:
            result["delinquency"] = delinquency_info
        
        # 시나리오 라벨
        scenario_label = await self.get_scenario_label(user_id)
        if "error" not in scenario_label:
            result["scenario"] = scenario_label
        
        # 지출 패턴
        spending_pattern = await self.get_spending_pattern(user_id)
        if "error" not in spending_pattern:
            result["spending"] = spending_pattern
        
        # 금융 건강 점수 계산
        result["financial_health"] = await self.calculate_financial_health(user_id, result)
        
        return result
    
    async def calculate_financial_health(self, user_id: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자의 금융 건강 점수 계산"""
        health_score = 50  # 기본 점수
        
        # 잔액 정보 기반 점수 조정
        if "balance" in financial_data:
            balance = financial_data["balance"]
            
            # 대출 대비 예금 비율
            if balance.get("balance_loan", 0) > 0:
                loan_to_deposit_ratio = balance.get("balance", 0) / balance.get("balance_loan", 1)
                if loan_to_deposit_ratio > 2:
                    health_score += 10
                elif loan_to_deposit_ratio > 1:
                    health_score += 5
                elif loan_to_deposit_ratio < 0.5:
                    health_score -= 10
                elif loan_to_deposit_ratio < 1:
                    health_score -= 5
        
        # 연체 정보 기반 점수 조정
        if "delinquency" in financial_data:
            delinquency = financial_data["delinquency"]
            
            if delinquency.get("is_delinquent") == "Y":
                health_score -= 20
            
            if delinquency.get("recent_delinquent_days", 0) > 30:
                health_score -= 15
            elif delinquency.get("recent_delinquent_days", 0) > 0:
                health_score -= 5
        
        # 카드 사용 정보 기반 점수 조정
        if "card_usage" in financial_data and "balance" in financial_data:
            card = financial_data["card_usage"]
            balance = financial_data["balance"]
            
            # 신용카드 사용액 대비 잔액 비율
            if card.get("credit_usage_3m", 0) > 0:
                credit_to_balance_ratio = balance.get("balance", 0) / card.get("credit_usage_3m", 1)
                if credit_to_balance_ratio > 3:
                    health_score += 10
                elif credit_to_balance_ratio > 1:
                    health_score += 5
                elif credit_to_balance_ratio < 0.3:
                    health_score -= 10
                elif credit_to_balance_ratio < 0.7:
                    health_score -= 5
        
        # 시나리오 라벨 기반 점수 조정
        if "scenario" in financial_data:
            scenario = financial_data["scenario"]
            
            # DTI 비율
            dti = scenario.get("dti_estimate", 0)
            if dti > 0.5:
                health_score -= 15
            elif dti > 0.3:
                health_score -= 5
            elif dti < 0.2:
                health_score += 10
            
            # 부채 비율
            debt_ratio = scenario.get("debt_ratio", 0)
            if debt_ratio > 0.5:
                health_score -= 10
            elif debt_ratio > 0.3:
                health_score -= 5
            elif debt_ratio < 0.1:
                health_score += 10
        
        # 점수 범위 조정 (0-100)
        health_score = max(0, min(100, health_score))
        
        # 금융 건강 등급 결정
        if health_score >= 80:
            health_grade = "우수"
            description = "금융 건강 상태가 매우 양호합니다."
        elif health_score >= 60:
            health_grade = "양호"
            description = "금융 건강 상태가 양호합니다."
        elif health_score >= 40:
            health_grade = "보통"
            description = "금융 건강 상태가 보통입니다."
        elif health_score >= 20:
            health_grade = "주의"
            description = "금융 건강 상태에 주의가 필요합니다."
        else:
            health_grade = "위험"
            description = "금융 건강 상태가 위험합니다."
        
        # 개선 권장사항
        recommendations = []
        
        if "delinquency" in financial_data and financial_data["delinquency"].get("is_delinquent") == "Y":
            recommendations.append("연체 상태를 해소하는 것이 시급합니다.")
        
        if "scenario" in financial_data and financial_data["scenario"].get("debt_ratio", 0) > 0.4:
            recommendations.append("부채 비율이 높습니다. 부채 상환 계획을 세우세요.")
        
        if "balance" in financial_data and financial_data["balance"].get("balance_loan", 0) > financial_data["balance"].get("balance", 0):
            recommendations.append("대출 금액이 예금보다 많습니다. 저축을 늘리는 것이 좋습니다.")
        
        if "card_usage" in financial_data and financial_data["card_usage"].get("credit_usage_3m", 0) > financial_data["balance"].get("avg_balance_3m", 0) * 0.7:
            recommendations.append("신용카드 사용액이 많습니다. 지출을 줄이는 것이 좋습니다.")
        
        if len(recommendations) == 0:
            recommendations.append("현재 금융 상태를 유지하세요.")
        
        return {
            "score": health_score,
            "grade": health_grade,
            "description": description,
            "recommendations": recommendations
        }


# 싱글톤 인스턴스
_user_financial_service = None

def get_user_financial_service() -> UserFinancialService:
    """사용자 금융 서비스 싱글톤 인스턴스 반환"""
    global _user_financial_service
    if _user_financial_service is None:
        _user_financial_service = UserFinancialService()
    return _user_financial_service
