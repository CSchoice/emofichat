"""
적금 상품 서비스

적금 상품 정보를 조회하고 추천하는 서비스
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc

from app.core.db import SessionMaker
from app.models.financial_data import (
    SavingProduct, SavingProductOption, BankCompany
)
from app.services.database.user_financial_service import get_user_financial_service

logger = logging.getLogger(__name__)


class SavingProductService:
    """적금 상품 서비스 클래스"""
    
    async def get_db_session(self) -> AsyncSession:
        """데이터베이스 세션 가져오기"""
        return SessionMaker()
    
    async def get_all_bank_companies(self) -> List[Dict[str, Any]]:
        """모든 은행 회사 목록 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(select(BankCompany))
            companies = result.scalars().all()
            
            return [
                {
                    "fin_co_no": company.fin_co_no,
                    "kor_co_nm": company.kor_co_nm
                }
                for company in companies
            ]
    
    async def get_saving_products(self, fin_co_no: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """적금 상품 목록 조회"""
        async with await self.get_db_session() as session:
            query = select(SavingProduct)
            
            if fin_co_no:
                query = query.where(SavingProduct.fin_co_no == fin_co_no)
            
            query = query.limit(limit)
            result = await session.execute(query)
            products = result.scalars().all()
            
            product_list = []
            for product in products:
                # 회사 정보 조회
                company_result = await session.execute(
                    select(BankCompany).where(BankCompany.fin_co_no == product.fin_co_no)
                )
                company = company_result.scalars().first()
                
                # 옵션 정보 조회
                options_result = await session.execute(
                    select(SavingProductOption).where(SavingProductOption.fin_prdt_cd == product.fin_prdt_cd)
                )
                options = options_result.scalars().all()
                
                product_list.append({
                    "fin_prdt_cd": product.fin_prdt_cd,
                    "dcls_month": product.dcls_month,
                    "company": {
                        "fin_co_no": company.fin_co_no if company else None,
                        "kor_co_nm": company.kor_co_nm if company else "Unknown"
                    },
                    "fin_prdt_nm": product.fin_prdt_nm,
                    "join_way": product.join_way,
                    "mtrt_int": product.mtrt_int,
                    "spcl_cnd": product.spcl_cnd,
                    "join_deny": product.join_deny,
                    "join_member": product.join_member,
                    "etc_note": product.etc_note,
                    "max_limit": float(product.max_limit) if product.max_limit else None,
                    "dcls_strt_day": product.dcls_strt_day,
                    "dcls_end_day": product.dcls_end_day,
                    "options": [
                        {
                            "id": option.id,
                            "intr_rate_type": option.intr_rate_type,
                            "intr_rate_type_nm": option.intr_rate_type_nm,
                            "rsrv_type": option.rsrv_type,
                            "rsrv_type_nm": option.rsrv_type_nm,
                            "save_trm": option.save_trm,
                            "intr_rate": float(option.intr_rate) if option.intr_rate else None,
                            "intr_rate2": float(option.intr_rate2) if option.intr_rate2 else None
                        }
                        for option in options
                    ]
                })
            
            return product_list
    
    async def get_product_by_id(self, fin_prdt_cd: str) -> Dict[str, Any]:
        """상품 ID로 적금 상품 정보 조회"""
        async with await self.get_db_session() as session:
            result = await session.execute(
                select(SavingProduct).where(SavingProduct.fin_prdt_cd == fin_prdt_cd)
            )
            product = result.scalars().first()
            
            if not product:
                return {"error": "적금 상품을 찾을 수 없습니다."}
            
            # 회사 정보 조회
            company_result = await session.execute(
                select(BankCompany).where(BankCompany.fin_co_no == product.fin_co_no)
            )
            company = company_result.scalars().first()
            
            # 옵션 정보 조회
            options_result = await session.execute(
                select(SavingProductOption).where(SavingProductOption.fin_prdt_cd == product.fin_prdt_cd)
            )
            options = options_result.scalars().all()
            
            return {
                "fin_prdt_cd": product.fin_prdt_cd,
                "dcls_month": product.dcls_month,
                "company": {
                    "fin_co_no": company.fin_co_no if company else None,
                    "kor_co_nm": company.kor_co_nm if company else "Unknown"
                },
                "fin_prdt_nm": product.fin_prdt_nm,
                "join_way": product.join_way,
                "mtrt_int": product.mtrt_int,
                "spcl_cnd": product.spcl_cnd,
                "join_deny": product.join_deny,
                "join_member": product.join_member,
                "etc_note": product.etc_note,
                "max_limit": float(product.max_limit) if product.max_limit else None,
                "dcls_strt_day": product.dcls_strt_day,
                "dcls_end_day": product.dcls_end_day,
                "options": [
                    {
                        "id": option.id,
                        "intr_rate_type": option.intr_rate_type,
                        "intr_rate_type_nm": option.intr_rate_type_nm,
                        "rsrv_type": option.rsrv_type,
                        "rsrv_type_nm": option.rsrv_type_nm,
                        "save_trm": option.save_trm,
                        "intr_rate": float(option.intr_rate) if option.intr_rate else None,
                        "intr_rate2": float(option.intr_rate2) if option.intr_rate2 else None
                    }
                    for option in options
                ]
            }
    
    async def recommend_products_for_user(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """사용자에게 맞는 적금 상품 추천"""
        # 사용자 금융 정보 조회
        user_financial_service = get_user_financial_service()
        financial_summary = await user_financial_service.get_user_financial_summary(user_id)
        
        if "error" in financial_summary:
            # 사용자 정보가 없으면 기본 상품 추천
            products = await self.get_saving_products(limit=limit)
            for product in products:
                product["score"] = 0.5
                product["reasons"] = ["기본 추천 적금 상품입니다."]
            return products
        
        # 사용자 정보 기반 맞춤형 추천
        async with await self.get_db_session() as session:
            # 모든 적금 상품 조회
            result = await session.execute(select(SavingProduct))
            all_products = result.scalars().all()
            
            scored_products = []
            for product in all_products:
                score = 0.5  # 기본 점수
                reasons = []
                
                # 회사 정보 조회
                company_result = await session.execute(
                    select(BankCompany).where(BankCompany.fin_co_no == product.fin_co_no)
                )
                company = company_result.scalars().first()
                
                # 옵션 정보 조회
                options_result = await session.execute(
                    select(SavingProductOption).where(SavingProductOption.fin_prdt_cd == product.fin_prdt_cd)
                )
                options = options_result.scalars().all()
                
                # 최고 금리 옵션 찾기
                max_rate_option = None
                max_rate = 0
                
                for option in options:
                    if option.intr_rate and float(option.intr_rate) > max_rate:
                        max_rate = float(option.intr_rate)
                        max_rate_option = option
                
                # 사용자 금융 건강 상태에 따른 점수 조정
                financial_health = financial_summary.get("financial_health", {})
                health_score = financial_health.get("score", 50)
                
                # 금융 건강 점수가 낮은 경우 단기 적금 추천
                if health_score < 40:
                    short_term_options = [o for o in options if o.save_trm and o.save_trm <= 12]
                    if short_term_options:
                        score += 0.2
                        reasons.append("단기 적금 상품으로 유동성을 확보할 수 있습니다.")
                    
                    if product.max_limit and product.max_limit < 10000000:
                        score += 0.1
                        reasons.append("소액으로 시작할 수 있는 적금 상품입니다.")
                
                # 금융 건강 점수가 높은 경우 고금리 장기 적금 추천
                elif health_score > 70:
                    long_term_options = [o for o in options if o.save_trm and o.save_trm >= 24]
                    if long_term_options:
                        score += 0.1
                        reasons.append("장기 적금 상품으로 안정적인 수익을 얻을 수 있습니다.")
                    
                    if max_rate_option and max_rate > 3.0:
                        score += 0.2
                        reasons.append(f"높은 금리({max_rate}%)를 제공하는 적금 상품입니다.")
                
                # 잔액 정보에 따른 점수 조정
                balance_info = financial_summary.get("balance", {})
                avg_balance = balance_info.get("avg_balance_3m", 0)
                
                if avg_balance < 5000000 and product.max_limit and product.max_limit < 10000000:
                    score += 0.1
                    reasons.append("현재 잔액에 적합한 소액 적금 상품입니다.")
                elif avg_balance >= 5000000 and product.max_limit and product.max_limit >= 10000000:
                    score += 0.1
                    reasons.append("현재 잔액에 적합한 고액 적금 상품입니다.")
                
                # 카드 사용 패턴에 따른 점수 조정
                card_usage = financial_summary.get("card_usage", {})
                credit_usage = card_usage.get("credit_usage_3m", 0)
                
                if credit_usage > avg_balance * 0.5:
                    # 카드 사용액이 많은 경우 자동이체 적금 추천
                    if product.join_way and "자동이체" in product.join_way:
                        score += 0.1
                        reasons.append("자동이체 기능으로 꾸준한 저축이 가능한 상품입니다.")
                
                # 기본 정보 추가
                product_info = {
                    "fin_prdt_cd": product.fin_prdt_cd,
                    "company": {
                        "fin_co_no": company.fin_co_no if company else None,
                        "kor_co_nm": company.kor_co_nm if company else "Unknown"
                    },
                    "fin_prdt_nm": product.fin_prdt_nm,
                    "join_way": product.join_way,
                    "max_limit": float(product.max_limit) if product.max_limit else None,
                    "max_rate": max_rate,
                    "options": [
                        {
                            "save_trm": option.save_trm,
                            "intr_rate": float(option.intr_rate) if option.intr_rate else None,
                            "intr_rate2": float(option.intr_rate2) if option.intr_rate2 else None
                        }
                        for option in options[:3]  # 상위 3개 옵션만 포함
                    ],
                    "score": score,
                    "reasons": reasons
                }
                
                # 이유가 없으면 기본 이유 추가
                if not reasons:
                    if max_rate > 0:
                        product_info["reasons"].append(f"금리 {max_rate}%를 제공하는 적금 상품입니다.")
                    else:
                        product_info["reasons"].append("일반 적금 상품입니다.")
                
                scored_products.append(product_info)
            
            # 점수 기준으로 정렬하여 상위 N개 선택
            recommended_products = sorted(scored_products, key=lambda x: x["score"], reverse=True)[:limit]
            
            return recommended_products


# 싱글톤 인스턴스
_saving_product_service = None

def get_saving_product_service() -> SavingProductService:
    """적금 상품 서비스 싱글톤 인스턴스 반환"""
    global _saving_product_service
    if _saving_product_service is None:
        _saving_product_service = SavingProductService()
    return _saving_product_service
