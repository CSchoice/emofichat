"""
금융 상품 추천 API 엔드포인트

사용자의 감정 상태와 재무 프로필을 기반으로 맞춤형 금융 상품을 추천합니다.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from typing import Dict, List, Any, Optional
import logging
import json

from app.services.database.db_service import get_db_service
from app.core.cache import get_product_cache
from app.models import ProductRecommendation

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recommendations/{user_id}/{product_type}", response_model=ProductRecommendation)
async def get_product_recommendations(
    user_id: str,
    product_type: str,
    request: Request,
    limit: int = 3,
    refresh: bool = False
):
    """
    사용자에게 맞춤형 금융 상품을 추천합니다.
    
    - **user_id**: 사용자 ID
    - **product_type**: 상품 유형 (deposit, fund)
    - **limit**: 추천 상품 개수
    - **refresh**: 캐시를 무시하고 새로 추천 결과를 생성할지 여부
    """
    try:
        db_service = get_db_service()
        product_cache = get_product_cache()
        
        # 캐시된 추천 결과 조회 (refresh가 False인 경우)
        if not refresh:
            cached_recommendation = await product_cache.get_recommendation(user_id, product_type)
            if cached_recommendation:
                return ProductRecommendation(
                    product_type=product_type,
                    products=cached_recommendation.get("recommendations", [])
                )
        
        # 사용자 감정 데이터 조회
        emotion_trend = await db_service.get_emotion_trend(user_id, days=7)
        
        # 사용자 재무 프로필 조회
        financial_profile = await db_service.get_or_create_financial_profile(user_id)
        
        # 상품 목록 조회
        products = await db_service.get_products_by_type(product_type, limit=10)
        
        if not products:
            return ProductRecommendation(
                product_type=product_type,
                products=[]
            )
        
        # 추천 점수 계산
        scored_products = []
        for product in products:
            # 상품 데이터 변환
            # features가 문자열로 저장되어 있을 경우 JSON으로 파싱
            features = product.features
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except json.JSONDecodeError:
                    features = {}
            elif features is None:
                features = {}
                
            product_data = {
                "id": product.id,
                "product_id": product.product_id,
                "name": product.name,
                "type": product.type,
                "description": product.description,
                "interest_rate": product.interest_rate,
                "min_period": product.min_period,
                "max_period": product.max_period,
                "min_amount": product.min_amount,
                "risk_level": product.risk_level,
                "features": features
            }
            
            # 감정 상태에 따른 점수 계산
            emotion_score = 0.5  # 기본값
            if emotion_trend.get("data_points", 0) > 0:
                # 부정적 감정이 높은 경우 안정적인 상품 선호
                if emotion_trend.get("negative_ratio", 0.0) > 0.6:
                    if product.risk_level == "low":
                        emotion_score = 0.8
                    elif product.risk_level == "medium":
                        emotion_score = 0.5
                    else:
                        emotion_score = 0.2
                # 불안 감정이 높은 경우 안정적인 상품 선호
                elif emotion_trend.get("anxious_ratio", 0.0) > 0.6:
                    if product.risk_level == "low":
                        emotion_score = 0.9
                    elif product.risk_level == "medium":
                        emotion_score = 0.4
                    else:
                        emotion_score = 0.1
                # 감정 변동성이 높은 경우 안정적인 상품 선호
                elif emotion_trend.get("emotion_volatility", 0.0) > 0.7:
                    if product.risk_level == "low":
                        emotion_score = 0.7
                    elif product.risk_level == "medium":
                        emotion_score = 0.5
                    else:
                        emotion_score = 0.3
                # 일반적인 경우 균형 있는 점수
                else:
                    if product.risk_level == "low":
                        emotion_score = 0.6
                    elif product.risk_level == "medium":
                        emotion_score = 0.7
                    else:
                        emotion_score = 0.5
            
            # 재무 프로필에 따른 점수 계산
            finance_score = 0.5  # 기본값
            
            # 최종 점수 계산 (감정 50%, 재무 50%)
            final_score = (emotion_score * 0.5) + (finance_score * 0.5)
            
            # 추천 이유 생성
            reasons = []
            if product.risk_level == "low":
                reasons.append("안정적인 수익을 제공하는 상품입니다.")
            elif product.risk_level == "medium":
                reasons.append("적절한 위험과 수익의 균형을 갖춘 상품입니다.")
            else:
                reasons.append("높은 수익 가능성이 있는 상품입니다.")
            
            if product.type == "deposit":
                if product.interest_rate and product.interest_rate > 3.5:
                    reasons.append(f"현재 시장 대비 높은 금리({product.interest_rate}%)를 제공합니다.")
                if product.min_amount and product.min_amount <= 100000:
                    reasons.append("소액으로도 시작할 수 있는 상품입니다.")
            elif product.type == "fund":
                if product_data["features"].get("fund_type") == "bond":
                    reasons.append("안정적인 채권형 상품으로 변동성이 낮습니다.")
                elif product_data["features"].get("fund_type") == "equity":
                    reasons.append("주식형 상품으로 장기적인 성장 가능성이 있습니다.")
            
            # 감정 상태에 따른 추천 이유 추가
            if emotion_trend.get("data_points", 0) > 0:
                if emotion_trend.get("negative_ratio", 0.0) > 0.6 and product.risk_level == "low":
                    reasons.append("현재 감정 상태를 고려할 때 안정적인 상품이 적합합니다.")
                elif emotion_trend.get("anxious_ratio", 0.0) > 0.6 and product.risk_level == "low":
                    reasons.append("불안감을 줄이기 위해 안정적인 상품을 추천합니다.")
            
            # 추천 결과에 추가
            product_data["score"] = final_score
            product_data["reasons"] = reasons
            scored_products.append(product_data)
        
        # 점수 기준으로 정렬하여 상위 N개 선택
        recommended_products = sorted(scored_products, key=lambda x: x["score"], reverse=True)[:limit]
        
        # 추천 결과 캐싱
        await product_cache.cache_recommendation(user_id, product_type, recommended_products)
        
        # 추천 결과 저장 (백그라운드 작업으로 처리)
        for product in recommended_products:
            await db_service.save_recommendation(
                user_id=user_id,
                product_id=product["id"],
                score=product["score"],
                explanation=", ".join(product.get("reasons", []))
            )
        
        # 응답 구성
        response = ProductRecommendation(
            product_type=product_type,
            products=recommended_products
        )
        
        return response
        
    except Exception as e:
        logger.error(f"상품 추천 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="금융 상품을 추천하는 중 오류가 발생했습니다."
        )


@router.get("/recommendations/history/{user_id}", response_model=List[Dict[str, Any]])
async def get_recommendation_history(
    user_id: str,
    request: Request,
    limit: int = 5
):
    """
    사용자의 추천 이력을 조회합니다.
    
    - **user_id**: 사용자 ID
    - **limit**: 조회할 추천 이력 개수
    """
    try:
        db_service = get_db_service()
        
        # 추천 이력 조회
        recommendations = await db_service.get_user_recommendations(user_id, limit)
        
        return recommendations
        
    except Exception as e:
        logger.error(f"추천 이력 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="추천 이력을 조회하는 중 오류가 발생했습니다."
        )
