"""
펀드 상품 서비스

펀드 상품 정보를 조회하고 추천하는 서비스
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.core.db import SessionMaker
from app.models.financial_data import (
    Fund, FundCompany, FundType, FundPerformance
)
from app.services.database.user_financial_service import get_user_financial_service

logger = logging.getLogger(__name__)


class FundService:
    """펀드 상품 서비스 클래스"""
    
    async def get_db_session(self) -> AsyncSession:
        """데이터베이스 세션 가져오기"""
        return SessionMaker()
    
    async def get_all_fund_companies(self) -> List[Dict[str, Any]]:
        """모든 펀드 회사 목록 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(select(FundCompany))
            companies = result.scalars().all()
            
            return [
                {
                    "company_id": company.company_id,
                    "company_name": company.company_name
                }
                for company in companies
            ]
    
    async def get_all_fund_types(self) -> List[Dict[str, Any]]:
        """모든 펀드 유형 목록 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(select(FundType))
            types = result.scalars().all()
            
            return [
                {
                    "type_id": fund_type.type_id,
                    "large_category": fund_type.large_category,
                    "mid_category": fund_type.mid_category,
                    "small_category": fund_type.small_category
                }
                for fund_type in types
            ]
    
    async def get_funds(self, company_id: Optional[int] = None, type_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """펀드 목록 조회"""
        async with await self.get_db_session() as session:
            query = select(Fund)
            
            if company_id:
                query = query.where(Fund.company_id == company_id)
            
            if type_id:
                query = query.where(Fund.type_id == type_id)
            
            query = query.limit(limit)
            result = await session.execute(query)
            funds = result.scalars().all()
            
            fund_list = []
            for fund in funds:
                # 회사 정보 조회
                company_result = await session.execute(
                    select(FundCompany).where(FundCompany.company_id == fund.company_id)
                )
                company = company_result.scalars().first()
                
                # 유형 정보 조회
                type_result = await session.execute(
                    select(FundType).where(FundType.type_id == fund.type_id)
                )
                fund_type = type_result.scalars().first()
                
                # 성과 정보 조회
                performance_result = await session.execute(
                    select(FundPerformance).where(FundPerformance.fund_id == fund.fund_id)
                )
                performance = performance_result.scalars().first()
                
                fund_list.append({
                    "fund_id": fund.fund_id,
                    "fund_name": fund.fund_name,
                    "company": {
                        "company_id": company.company_id if company else None,
                        "company_name": company.company_name if company else "Unknown"
                    },
                    "type": {
                        "type_id": fund_type.type_id if fund_type else None,
                        "large_category": fund_type.large_category if fund_type else None,
                        "mid_category": fund_type.mid_category if fund_type else None,
                        "small_category": fund_type.small_category if fund_type else None
                    },
                    "setup_date": fund.setup_date.isoformat() if fund.setup_date else None,
                    "performance": {
                        "return_1m": performance.return_1m if performance else None,
                        "return_3m": performance.return_3m if performance else None,
                        "return_6m": performance.return_6m if performance else None,
                        "return_1y": performance.return_1y if performance else None,
                        "stddev_1y": performance.stddev_1y if performance else None,
                        "sharpe_ratio_1y": performance.sharpe_ratio_1y if performance else None
                    } if performance else None
                })
            
            return fund_list
    
    async def get_fund_by_id(self, fund_id: str) -> Dict[str, Any]:
        """펀드 ID로 펀드 정보 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(Fund).where(Fund.fund_id == fund_id)
            )
            fund = result.scalars().first()
            
            if not fund:
                return {"error": "펀드를 찾을 수 없습니다."}
            
            # 회사 정보 조회
            company_result = await session.execute(
                select(FundCompany).where(FundCompany.company_id == fund.company_id)
            )
            company = company_result.scalars().first()
            
            # 유형 정보 조회
            type_result = await session.execute(
                select(FundType).where(FundType.type_id == fund.type_id)
            )
            fund_type = type_result.scalars().first()
            
            # 성과 정보 조회
            performance_result = await session.execute(
                select(FundPerformance).where(FundPerformance.fund_id == fund.fund_id)
            )
            performance = performance_result.scalars().first()
            
            return {
                "fund_id": fund.fund_id,
                "fund_name": fund.fund_name,
                "company": {
                    "company_id": company.company_id if company else None,
                    "company_name": company.company_name if company else "Unknown"
                },
                "type": {
                    "type_id": fund_type.type_id if fund_type else None,
                    "large_category": fund_type.large_category if fund_type else None,
                    "mid_category": fund_type.mid_category if fund_type else None,
                    "small_category": fund_type.small_category if fund_type else None
                },
                "setup_date": fund.setup_date.isoformat() if fund.setup_date else None,
                "performance": {
                    "return_1m": performance.return_1m if performance else None,
                    "return_3m": performance.return_3m if performance else None,
                    "return_6m": performance.return_6m if performance else None,
                    "return_1y": performance.return_1y if performance else None,
                    "stddev_1y": performance.stddev_1y if performance else None,
                    "sharpe_ratio_1y": performance.sharpe_ratio_1y if performance else None
                } if performance else None
            }
    
    async def recommend_funds_for_user(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """사용자에게 맞는 펀드 추천"""
        # 사용자 금융 정보 조회
        user_financial_service = get_user_financial_service()
        financial_summary = await user_financial_service.get_user_financial_summary(user_id)
        
        if "error" in financial_summary:
            # 사용자 정보가 없으면 기본 펀드 추천
            funds = await self.get_funds(limit=limit)
            for fund in funds:
                fund["score"] = 0.5
                fund["reasons"] = ["기본 추천 펀드입니다."]
            return funds
        
        # 사용자 정보 기반 맞춤형 추천
        async with await self.get_db_session() as session:
            # 모든 펀드 조회
            result = await session.execute(select(Fund))
            all_funds = result.scalars().all()
            
            scored_funds = []
            for fund in all_funds:
                score = 0.5  # 기본 점수
                reasons = []
                
                # 회사 정보 조회
                company_result = await session.execute(
                    select(FundCompany).where(FundCompany.company_id == fund.company_id)
                )
                company = company_result.scalars().first()
                
                # 유형 정보 조회
                type_result = await session.execute(
                    select(FundType).where(FundType.type_id == fund.type_id)
                )
                fund_type = type_result.scalars().first()
                
                # 성과 정보 조회
                performance_result = await session.execute(
                    select(FundPerformance).where(FundPerformance.fund_id == fund.fund_id)
                )
                performance = performance_result.scalars().first()
                
                # 사용자 금융 건강 상태에 따른 점수 조정
                financial_health = financial_summary.get("financial_health", {})
                health_score = financial_health.get("score", 50)
                
                # 금융 건강 점수가 낮은 경우 안전한 펀드 추천
                if health_score < 40:
                    if fund_type and fund_type.large_category == "채권형":
                        score += 0.2
                        reasons.append("안정적인 채권형 펀드입니다.")
                    
                    if performance and performance.stddev_1y and performance.stddev_1y < 5:
                        score += 0.1
                        reasons.append("변동성이 낮은 안정적인 펀드입니다.")
                
                # 금융 건강 점수가 높은 경우 수익성 높은 펀드 추천
                elif health_score > 70:
                    if fund_type and fund_type.large_category == "주식형":
                        score += 0.1
                        reasons.append("성장 가능성이 높은 주식형 펀드입니다.")
                    
                    if performance and performance.return_1y and performance.return_1y > 10:
                        score += 0.2
                        reasons.append(f"1년 수익률이 높은 펀드입니다({performance.return_1y}%).")
                    
                    if performance and performance.sharpe_ratio_1y and performance.sharpe_ratio_1y > 1:
                        score += 0.1
                        reasons.append("위험 대비 수익률이 우수한 펀드입니다.")
                
                # 중간 점수의 경우 혼합형 펀드 추천
                else:
                    if fund_type and fund_type.large_category == "혼합형":
                        score += 0.2
                        reasons.append("안정성과 수익성의 균형을 갖춘 혼합형 펀드입니다.")
                
                # 연령에 따른 점수 조정
                age = financial_summary.get("user", {}).get("age", 0)
                if age:
                    if age < 30 and fund_type and fund_type.large_category == "주식형":
                        score += 0.1
                        reasons.append("젊은 연령대에 적합한 성장형 펀드입니다.")
                    elif age > 50 and fund_type and fund_type.large_category == "채권형":
                        score += 0.1
                        reasons.append("장년층에 적합한 안정형 펀드입니다.")
                
                # 기본 정보 추가
                fund_info = {
                    "fund_id": fund.fund_id,
                    "fund_name": fund.fund_name,
                    "company": {
                        "company_id": company.company_id if company else None,
                        "company_name": company.company_name if company else "Unknown"
                    },
                    "type": {
                        "type_id": fund_type.type_id if fund_type else None,
                        "large_category": fund_type.large_category if fund_type else None,
                        "mid_category": fund_type.mid_category if fund_type else None,
                        "small_category": fund_type.small_category if fund_type else None
                    },
                    "setup_date": fund.setup_date.isoformat() if fund.setup_date else None,
                    "performance": {
                        "return_1m": performance.return_1m if performance else None,
                        "return_3m": performance.return_3m if performance else None,
                        "return_6m": performance.return_6m if performance else None,
                        "return_1y": performance.return_1y if performance else None,
                        "stddev_1y": performance.stddev_1y if performance else None,
                        "sharpe_ratio_1y": performance.sharpe_ratio_1y if performance else None
                    } if performance else None,
                    "score": score,
                    "reasons": reasons
                }
                
                # 이유가 없으면 기본 이유 추가
                if not reasons:
                    if fund_type:
                        fund_info["reasons"].append(f"{fund_type.large_category} 펀드입니다.")
                    else:
                        fund_info["reasons"].append("일반 펀드 상품입니다.")
                
                scored_funds.append(fund_info)
            
            # 점수 기준으로 정렬하여 상위 N개 선택
            recommended_funds = sorted(scored_funds, key=lambda x: x["score"], reverse=True)[:limit]
            
            return recommended_funds


# 싱글톤 인스턴스
_fund_service = None

def get_fund_service() -> FundService:
    """펀드 서비스 싱글톤 인스턴스 반환"""
    global _fund_service
    if _fund_service is None:
        _fund_service = FundService()
    return _fund_service
