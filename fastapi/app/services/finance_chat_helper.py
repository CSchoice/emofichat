"""
금융 상담 응답에 상품 추천을 통합하는 헬퍼 함수들.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

# 로거 설정
logger = logging.getLogger(__name__)

# 상품 추천 관련 함수
from app.services.product_formatter import format_product_recommendation
from app.services.product_recommender import PRODUCT_TYPE_DEPOSIT, PRODUCT_TYPE_FUND

def should_recommend_products(user_msg: str) -> Tuple[bool, Optional[str]]:
    """
    사용자 메시지를 분석하여 상품 추천이 필요한지 판단합니다.
    
    Returns:
        (추천 필요 여부, 추천할 상품 타입)
    """
    # 상품 추천 키워드
    product_keywords = {
        "예금": PRODUCT_TYPE_DEPOSIT,
        "적금": PRODUCT_TYPE_DEPOSIT,
        "정기예금": PRODUCT_TYPE_DEPOSIT,
        "입출금": PRODUCT_TYPE_DEPOSIT,
        "이자율": PRODUCT_TYPE_DEPOSIT,
        "금리": PRODUCT_TYPE_DEPOSIT,
        "펀드": PRODUCT_TYPE_FUND,
        "투자": PRODUCT_TYPE_FUND,
        "수익률": PRODUCT_TYPE_FUND,
        "주식형": PRODUCT_TYPE_FUND,
        "채권형": PRODUCT_TYPE_FUND,
        "상품": None,  # 일반적인 상품 언급
        "추천": None,  # 추천 요청
    }
    
    # 상품 추천 필요 여부 판단
    needs_product_recommendation = False
    product_type = None
    
    for keyword, ptype in product_keywords.items():
        if keyword in user_msg:
            needs_product_recommendation = True
            if ptype:  # 특정 상품 타입이 있는 경우
                product_type = ptype
                break
    
    # 상품 타입이 결정되지 않았으나 추천은 필요한 경우
    if needs_product_recommendation and not product_type:
        # "펀드" 또는 "투자" 관련 키워드가 있으면 펀드, 아니면 예금/적금으로 기본 설정
        if "펀드" in user_msg or "투자" in user_msg:
            product_type = PRODUCT_TYPE_FUND
        else:
            product_type = PRODUCT_TYPE_DEPOSIT
    
    return needs_product_recommendation, product_type

def integrate_product_recommendations(
    base_reply: str,
    products: List[Dict[str, Any]],
    product_type: str,
    emotion_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    기본 응답과 상품 추천을 통합합니다.
    
    Args:
        base_reply: 기본 응답 텍스트
        products: 추천 상품 목록
        product_type: 상품 유형 (deposit 또는 fund)
        emotion_data: 감정 분석 결과
        
    Returns:
        통합된 응답 텍스트
    """
    if not products:
        return base_reply
    
    product_text = format_product_recommendation(products, product_type, emotion_data)
    
    # 기본 응답과 상품 추천 통합
    # 문장이 끝나는 지점을 찾아 거기에 추가
    if base_reply.endswith(".") or base_reply.endswith("?") or base_reply.endswith("!"):
        combined_reply = f"{base_reply}\n\n{product_text}"
    else:
        combined_reply = f"{base_reply}.\n\n{product_text}"
    
    return combined_reply
