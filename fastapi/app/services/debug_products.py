"""
상품 추천 기능 디버깅 스크립트
"""
import asyncio
import logging
import sys
import json

from app.services.product_recommender import (
    recommend_products, 
    recommend_deposit_products,
    recommend_fund_products,
    PRODUCT_TYPE_DEPOSIT
)
from app.services.product_formatter import format_product_recommendation
from app.services.topic_detector import analyze_emotion

# 로거 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 테스트용 사용자 데이터
test_user_data = {
    "나이": 35,
    "성별": "M",
    "재정건전성": "양호",
    "유동성점수": 65.0,
    "연체여부": False,
    "balance_b0m": 5000000,
    "avg_balance_3m": 4800000,
    "card_usage_b0m": 1500000
}

test_emotion_data = {
    "dominant_emotion": "중립",
    "is_anxious": False
}

async def run_debug():
    """테스트 실행"""
    logger.info("===== 상품 추천 디버깅 시작 =====")
    
    # 1. 예금 상품 직접 조회 테스트
    logger.info("1. 예금 상품 직접 조회 테스트")
    deposit_products = await recommend_deposit_products(
        "test_user", test_user_data, test_emotion_data, limit=3
    )
    logger.info(f"예금 상품 조회 결과: {len(deposit_products)}개 상품")
    logger.debug(f"예금 상품 데이터: {json.dumps(deposit_products, ensure_ascii=False, indent=2)}")
    
    # 2. 상품 추천 통합 함수 테스트
    logger.info("2. 상품 추천 통합 함수 테스트")
    products = await recommend_products(
        "test_user", test_user_data, test_emotion_data, PRODUCT_TYPE_DEPOSIT, limit=3
    )
    logger.info(f"추천 상품 개수: {len(products)}개")
    logger.debug(f"추천 상품 데이터: {json.dumps(products, ensure_ascii=False, indent=2)}")
    
    # 3. 포맷팅 테스트
    logger.info("3. 포맷팅 테스트")
    formatted_products = format_product_recommendation(products, PRODUCT_TYPE_DEPOSIT, test_emotion_data)
    logger.info(f"포맷팅 결과 길이: {len(formatted_products)}")
    logger.info(f"포맷팅 결과: \n{formatted_products}")
    
    logger.info("===== 상품 추천 디버깅 종료 =====")

if __name__ == "__main__":
    asyncio.run(run_debug())
