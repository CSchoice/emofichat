"""
은행 상품 서비스

은행 상품 정보를 조회하고 추천하는 서비스
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.core.db import SessionMaker
from app.models.financial_data import (
    Bank, BankProduct, BankProductBenefit, BankProductChannel, ChannelMaster
)
from app.services.database.user_financial_service import get_user_financial_service

logger = logging.getLogger(__name__)


class BankProductService:
    """은행 상품 서비스 클래스"""
    
    async def get_db_session(self) -> AsyncSession:
        """데이터베이스 세션 가져오기"""
        return SessionMaker()
    
    async def get_all_banks(self) -> List[Dict[str, Any]]:
        """모든 은행 목록 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(select(Bank))
            banks = result.scalars().all()
            
            return [
                {
                    "bank_id": bank.bank_id,
                    "bank_name": bank.bank_name
                }
                for bank in banks
            ]
    
    async def get_bank_by_id(self, bank_id: int) -> Dict[str, Any]:
        """은행 ID로 은행 정보 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(Bank).where(Bank.bank_id == bank_id)
            )
            bank = result.scalars().first()
            
            if not bank:
                return {"error": "은행을 찾을 수 없습니다."}
            
            return {
                "bank_id": bank.bank_id,
                "bank_name": bank.bank_name
            }
    
    async def get_bank_products(self, bank_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """은행 상품 목록 조회"""
        async with await self.get_db_session() as session:
            query = select(BankProduct)
            
            if bank_id:
                query = query.where(BankProduct.bank_id == bank_id)
            
            query = query.limit(limit)
            result = await session.execute(query)
            products = result.scalars().all()
            
            product_list = []
            for product in products:
                # 은행 정보 조회
                bank_result = await session.execute(
                    select(Bank).where(Bank.bank_id == product.bank_id)
                )
                bank = bank_result.scalars().first()
                
                # 혜택 정보 조회
                benefits_result = await session.execute(
                    select(BankProductBenefit).where(BankProductBenefit.product_id == product.product_id)
                )
                benefits = benefits_result.scalars().all()
                
                # 채널 정보 조회
                channels_result = await session.execute(
                    select(BankProductChannel).where(BankProductChannel.product_id == product.product_id)
                )
                channels = channels_result.scalars().all()
                
                channel_info = []
                for channel in channels:
                    channel_master_result = await session.execute(
                        select(ChannelMaster).where(ChannelMaster.channel_code == channel.channel_code)
                    )
                    channel_master = channel_master_result.scalars().first()
                    if channel_master:
                        channel_info.append({
                            "channel_code": channel.channel_code,
                            "channel_name": channel_master.channel_name,
                            "channel_type": channel.channel_type
                        })
                
                product_list.append({
                    "product_id": product.product_id,
                    "bank": {
                        "bank_id": bank.bank_id if bank else None,
                        "bank_name": bank.bank_name if bank else "Unknown"
                    },
                    "product_name": product.product_name,
                    "description": product.description,
                    "min_period_days": product.min_period_days,
                    "max_period_days": product.max_period_days,
                    "min_amount": product.min_amount,
                    "max_amount": product.max_amount,
                    "deposit_method": product.deposit_method,
                    "maturity": product.maturity,
                    "interest_payment_method": product.interest_payment_method,
                    "interest_type": product.interest_type,
                    "base_interest_rate": product.base_interest_rate,
                    "protection": product.protection,
                    "benefits": [
                        {
                            "benefit_id": benefit.benefit_id,
                            "benefit_condition": benefit.benefit_condition,
                            "benefit_rate": benefit.benefit_rate
                        }
                        for benefit in benefits
                    ],
                    "channels": channel_info
                })
            
            return product_list
    
    async def get_product_by_id(self, product_id: str) -> Dict[str, Any]:
        """상품 ID로 상품 정보 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(BankProduct).where(BankProduct.product_id == product_id)
            )
            product = result.scalars().first()
            
            if not product:
                return {"error": "상품을 찾을 수 없습니다."}
            
            # 은행 정보 조회
            bank_result = await session.execute(
                select(Bank).where(Bank.bank_id == product.bank_id)
            )
            bank = bank_result.scalars().first()
            
            # 혜택 정보 조회
            benefits_result = await session.execute(
                select(BankProductBenefit).where(BankProductBenefit.product_id == product.product_id)
            )
            benefits = benefits_result.scalars().all()
            
            # 채널 정보 조회
            channels_result = await session.execute(
                select(BankProductChannel).where(BankProductChannel.product_id == product.product_id)
            )
            channels = channels_result.scalars().all()
            
            channel_info = []
            for channel in channels:
                channel_master_result = await session.execute(
                    select(ChannelMaster).where(ChannelMaster.channel_code == channel.channel_code)
                )
                channel_master = channel_master_result.scalars().first()
                if channel_master:
                    channel_info.append({
                        "channel_code": channel.channel_code,
                        "channel_name": channel_master.channel_name,
                        "channel_type": channel.channel_type
                    })
            
            return {
                "product_id": product.product_id,
                "bank": {
                    "bank_id": bank.bank_id if bank else None,
                    "bank_name": bank.bank_name if bank else "Unknown"
                },
                "product_name": product.product_name,
                "description": product.description,
                "min_period_days": product.min_period_days,
                "max_period_days": product.max_period_days,
                "min_amount": product.min_amount,
                "max_amount": product.max_amount,
                "deposit_method": product.deposit_method,
                "maturity": product.maturity,
                "interest_payment_method": product.interest_payment_method,
                "interest_type": product.interest_type,
                "base_interest_rate": product.base_interest_rate,
                "protection": product.protection,
                "benefits": [
                    {
                        "benefit_id": benefit.benefit_id,
                        "benefit_condition": benefit.benefit_condition,
                        "benefit_rate": benefit.benefit_rate
                    }
                    for benefit in benefits
                ],
                "channels": channel_info
            }
    
    async def recommend_products_for_user(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """사용자에게 맞는 은행 상품 추천"""
        # 사용자 금융 정보 조회
        user_financial_service = get_user_financial_service()
        financial_summary = await user_financial_service.get_user_financial_summary(user_id)
        
        if "error" in financial_summary:
            # 사용자 정보가 없으면 기본 상품 추천
            products = await self.get_bank_products(limit=limit)
            for product in products:
                product["score"] = 0.5
                product["reasons"] = ["기본 추천 상품입니다."]
            return products
        
        # 사용자 정보 기반 맞춤형 추천
        async with await self.get_db_session() as session:
            # 모든 상품 조회
            result = await session.execute(select(BankProduct))
            all_products = result.scalars().all()
            
            scored_products = []
            for product in all_products:
                score = 0.5  # 기본 점수
                reasons = []
                
                # 은행 정보 조회
                bank_result = await session.execute(
                    select(Bank).where(Bank.bank_id == product.bank_id)
                )
                bank = bank_result.scalars().first()
                
                # 혜택 정보 조회
                benefits_result = await session.execute(
                    select(BankProductBenefit).where(BankProductBenefit.product_id == product.product_id)
                )
                benefits = benefits_result.scalars().all()
                
                # 사용자 금융 건강 상태에 따른 점수 조정
                financial_health = financial_summary.get("financial_health", {})
                health_score = financial_health.get("score", 50)
                
                # 금융 건강 점수가 낮은 경우 안전한 상품 추천
                if health_score < 40:
                    if product.protection:
                        score += 0.2
                        reasons.append("원금 보장 상품으로 안전합니다.")
                    
                    if product.min_amount and product.min_amount < 1000000:
                        score += 0.1
                        reasons.append("소액으로 시작할 수 있는 상품입니다.")
                
                # 금융 건강 점수가 높은 경우 수익성 높은 상품 추천
                elif health_score > 70:
                    if product.base_interest_rate and product.base_interest_rate > 3.0:
                        score += 0.2
                        reasons.append(f"높은 기본 금리({product.base_interest_rate}%)를 제공합니다.")
                    
                    if len(benefits) > 0:
                        max_benefit_rate = max([b.benefit_rate or 0 for b in benefits], default=0)
                        if max_benefit_rate > 0.5:
                            score += 0.1
                            reasons.append(f"추가 우대금리 혜택이 있습니다.")
                
                # 잔액 정보에 따른 점수 조정
                balance_info = financial_summary.get("balance", {})
                avg_balance = balance_info.get("avg_balance_3m", 0)
                
                if product.min_amount and avg_balance >= product.min_amount:
                    score += 0.1
                    reasons.append("현재 잔액으로 가입 가능한 상품입니다.")
                
                if product.min_amount and product.max_amount:
                    if avg_balance >= product.min_amount and avg_balance <= product.max_amount:
                        score += 0.1
                        reasons.append("현재 잔액에 적합한 상품입니다.")
                
                # 카드 사용 패턴에 따른 점수 조정
                card_usage = financial_summary.get("card_usage", {})
                credit_usage = card_usage.get("credit_usage_3m", 0)
                
                if credit_usage > 0 and product.base_interest_rate:
                    if credit_usage > avg_balance * 0.7:
                        # 카드 사용액이 많은 경우 저축 상품 추천
                        score += 0.1
                        reasons.append("카드 사용액 대비 저축을 늘리는 데 도움이 되는 상품입니다.")
                
                # 기본 정보 추가
                product_info = {
                    "product_id": product.product_id,
                    "bank": {
                        "bank_id": bank.bank_id if bank else None,
                        "bank_name": bank.bank_name if bank else "Unknown"
                    },
                    "product_name": product.product_name,
                    "description": product.description,
                    "min_period_days": product.min_period_days,
                    "max_period_days": product.max_period_days,
                    "min_amount": product.min_amount,
                    "max_amount": product.max_amount,
                    "interest_type": product.interest_type,
                    "base_interest_rate": product.base_interest_rate,
                    "protection": product.protection,
                    "score": score,
                    "reasons": reasons
                }
                
                # 이유가 없으면 기본 이유 추가
                if not reasons:
                    if product.protection:
                        product_info["reasons"].append("안전한 금융 상품입니다.")
                    elif product.base_interest_rate:
                        product_info["reasons"].append(f"기본 금리 {product.base_interest_rate}%를 제공합니다.")
                    else:
                        product_info["reasons"].append("일반 금융 상품입니다.")
                
                scored_products.append(product_info)
            
            # 점수 기준으로 정렬하여 상위 N개 선택
            recommended_products = sorted(scored_products, key=lambda x: x["score"], reverse=True)[:limit]
            
            return recommended_products


# 싱글톤 인스턴스
_bank_product_service = None

def get_bank_product_service() -> BankProductService:
    """은행 상품 서비스 싱글톤 인스턴스 반환"""
    global _bank_product_service
    if _bank_product_service is None:
        _bank_product_service = BankProductService()
    return _bank_product_service
