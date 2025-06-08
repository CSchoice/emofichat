"""
금융 데이터 API 엔드포인트

사용자의 금융 데이터를 조회하고 분석하는 API를 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict, List, Any, Optional
import logging

from app.services.database.user_financial_service import get_user_financial_service
from app.services.database.bank_product_service import get_bank_product_service
from app.services.database.fund_service import get_fund_service
from app.services.database.saving_product_service import get_saving_product_service

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/financial-data/{user_id}", response_model=Dict[str, Any])
async def get_user_financial_data(user_id: str, request: Request):
    """
    사용자의 금융 데이터 종합 정보를 조회합니다.
    
    - **user_id**: 사용자 ID
    """
    try:
        user_financial_service = get_user_financial_service()
        financial_summary = await user_financial_service.get_user_financial_summary(user_id)
        
        if "error" in financial_summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=financial_summary["error"]
            )
        
        return financial_summary
        
    except Exception as e:
        logger.error(f"금융 데이터 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="금융 데이터를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/financial-health/{user_id}", response_model=Dict[str, Any])
async def get_user_financial_health(user_id: str, request: Request):
    """
    사용자의 금융 건강 상태를 조회합니다.
    
    - **user_id**: 사용자 ID
    """
    try:
        user_financial_service = get_user_financial_service()
        financial_summary = await user_financial_service.get_user_financial_summary(user_id)
        
        if "error" in financial_summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=financial_summary["error"]
            )
        
        return financial_summary.get("financial_health", {})
        
    except Exception as e:
        logger.error(f"금융 건강 상태 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="금융 건강 상태를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/bank-products", response_model=List[Dict[str, Any]])
async def get_bank_products(request: Request, bank_id: Optional[int] = None, limit: int = 10):
    """
    은행 상품 목록을 조회합니다.
    
    - **bank_id**: (선택) 특정 은행의 상품만 조회
    - **limit**: 조회할 최대 상품 수
    """
    try:
        bank_product_service = get_bank_product_service()
        products = await bank_product_service.get_bank_products(bank_id=bank_id, limit=limit)
        
        return products
        
    except Exception as e:
        logger.error(f"은행 상품 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="은행 상품을 조회하는 중 오류가 발생했습니다."
        )


@router.get("/bank-products/{product_id}", response_model=Dict[str, Any])
async def get_bank_product_detail(product_id: str, request: Request):
    """
    특정 은행 상품의 상세 정보를 조회합니다.
    
    - **product_id**: 상품 ID
    """
    try:
        bank_product_service = get_bank_product_service()
        product = await bank_product_service.get_product_by_id(product_id)
        
        if "error" in product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=product["error"]
            )
        
        return product
        
    except Exception as e:
        logger.error(f"은행 상품 상세 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="은행 상품 상세 정보를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/bank-products/recommend/{user_id}", response_model=List[Dict[str, Any]])
async def recommend_bank_products(user_id: str, request: Request, limit: int = 5):
    """
    사용자에게 맞는 은행 상품을 추천합니다.
    
    - **user_id**: 사용자 ID
    - **limit**: 추천할 최대 상품 수
    """
    try:
        bank_product_service = get_bank_product_service()
        recommended_products = await bank_product_service.recommend_products_for_user(user_id, limit=limit)
        
        return recommended_products
        
    except Exception as e:
        logger.error(f"은행 상품 추천 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="은행 상품 추천 중 오류가 발생했습니다."
        )


@router.get("/funds", response_model=List[Dict[str, Any]])
async def get_funds(
    request: Request, 
    company_id: Optional[int] = None, 
    type_id: Optional[int] = None, 
    limit: int = 10
):
    """
    펀드 목록을 조회합니다.
    
    - **company_id**: (선택) 특정 회사의 펀드만 조회
    - **type_id**: (선택) 특정 유형의 펀드만 조회
    - **limit**: 조회할 최대 펀드 수
    """
    try:
        fund_service = get_fund_service()
        funds = await fund_service.get_funds(company_id=company_id, type_id=type_id, limit=limit)
        
        return funds
        
    except Exception as e:
        logger.error(f"펀드 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="펀드를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/funds/{fund_id}", response_model=Dict[str, Any])
async def get_fund_detail(fund_id: str, request: Request):
    """
    특정 펀드의 상세 정보를 조회합니다.
    
    - **fund_id**: 펀드 ID
    """
    try:
        fund_service = get_fund_service()
        fund = await fund_service.get_fund_by_id(fund_id)
        
        if "error" in fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=fund["error"]
            )
        
        return fund
        
    except Exception as e:
        logger.error(f"펀드 상세 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="펀드 상세 정보를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/funds/recommend/{user_id}", response_model=List[Dict[str, Any]])
async def recommend_funds(user_id: str, request: Request, limit: int = 5):
    """
    사용자에게 맞는 펀드를 추천합니다.
    
    - **user_id**: 사용자 ID
    - **limit**: 추천할 최대 펀드 수
    """
    try:
        fund_service = get_fund_service()
        recommended_funds = await fund_service.recommend_funds_for_user(user_id, limit=limit)
        
        return recommended_funds
        
    except Exception as e:
        logger.error(f"펀드 추천 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="펀드 추천 중 오류가 발생했습니다."
        )


@router.get("/saving-products", response_model=List[Dict[str, Any]])
async def get_saving_products(request: Request, fin_co_no: Optional[str] = None, limit: int = 10):
    """
    적금 상품 목록을 조회합니다.
    
    - **fin_co_no**: (선택) 특정 금융회사의 적금 상품만 조회
    - **limit**: 조회할 최대 상품 수
    """
    try:
        saving_product_service = get_saving_product_service()
        products = await saving_product_service.get_saving_products(fin_co_no=fin_co_no, limit=limit)
        
        return products
        
    except Exception as e:
        logger.error(f"적금 상품 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="적금 상품을 조회하는 중 오류가 발생했습니다."
        )


@router.get("/saving-products/{fin_prdt_cd}", response_model=Dict[str, Any])
async def get_saving_product_detail(fin_prdt_cd: str, request: Request):
    """
    특정 적금 상품의 상세 정보를 조회합니다.
    
    - **fin_prdt_cd**: 적금 상품 코드
    """
    try:
        saving_product_service = get_saving_product_service()
        product = await saving_product_service.get_product_by_id(fin_prdt_cd)
        
        if "error" in product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=product["error"]
            )
        
        return product
        
    except Exception as e:
        logger.error(f"적금 상품 상세 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="적금 상품 상세 정보를 조회하는 중 오류가 발생했습니다."
        )


@router.get("/saving-products/recommend/{user_id}", response_model=List[Dict[str, Any]])
async def recommend_saving_products(user_id: str, request: Request, limit: int = 5):
    """
    사용자에게 맞는 적금 상품을 추천합니다.
    
    - **user_id**: 사용자 ID
    - **limit**: 추천할 최대 상품 수
    """
    try:
        saving_product_service = get_saving_product_service()
        recommended_products = await saving_product_service.recommend_products_for_user(user_id, limit=limit)
        
        return recommended_products
        
    except Exception as e:
        logger.error(f"적금 상품 추천 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="적금 상품 추천 중 오류가 발생했습니다."
        )


@router.get("/financial-products/recommend/{user_id}", response_model=Dict[str, Any])
async def recommend_all_financial_products(user_id: str, request: Request, limit: int = 3):
    """
    사용자에게 맞는 모든 종류의 금융 상품을 추천합니다.
    
    - **user_id**: 사용자 ID
    - **limit**: 각 카테고리별 추천할 최대 상품 수
    """
    try:
        bank_product_service = get_bank_product_service()
        fund_service = get_fund_service()
        saving_product_service = get_saving_product_service()
        
        # 각 서비스에서 추천 상품 조회
        bank_products = await bank_product_service.recommend_products_for_user(user_id, limit=limit)
        funds = await fund_service.recommend_funds_for_user(user_id, limit=limit)
        saving_products = await saving_product_service.recommend_products_for_user(user_id, limit=limit)
        
        # 결과 통합
        return {
            "bank_products": bank_products,
            "funds": funds,
            "saving_products": saving_products
        }
        
    except Exception as e:
        logger.error(f"금융 상품 추천 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="금융 상품 추천 중 오류가 발생했습니다."
        )
