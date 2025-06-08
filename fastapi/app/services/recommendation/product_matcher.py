"""
금융상품 매칭 엔진

사용자의 재무 상태와 감정 상태를 바탕으로 적합한 금융상품을 추천합니다.
"""

import logging
from typing import Dict, Any, List, Optional

# 로거 설정
logger = logging.getLogger(__name__)

# 상품 유형 상수
PRODUCT_TYPE_DEPOSIT = "deposit"  # 예금/적금
PRODUCT_TYPE_FUND = "fund"       # 펀드

class ProductMatcher:
    """금융상품 매칭 클래스"""
    
    def __init__(self, db_client=None):
        self.db = db_client
        
    async def recommend_products(
        self, 
        user_id: str, 
        user_data: Dict[str, Any], 
        emotion_data: Dict[str, Any],
        product_type: str = PRODUCT_TYPE_DEPOSIT,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        사용자에게 적합한 금융상품 추천
        
        Args:
            user_id: 사용자 ID
            user_data: 사용자 재무 데이터
            emotion_data: 감정 분석 결과
            product_type: 상품 유형 (deposit 또는 fund)
            limit: 추천할 상품 수
            
        Returns:
            추천 상품 목록
        """
        try:
            # 상품 목록 조회
            products = await self._get_products(product_type)
            
            # 상품이 없는 경우
            if not products:
                logger.warning(f"추천할 {product_type} 상품이 없습니다.")
                return []
                
            # 사용자 데이터가 없는 경우
            if not user_data:
                # 기본 추천 (인기 상품)
                return products[:limit]
                
            # 사용자 맞춤 추천
            scored_products = self._score_products(products, user_data, emotion_data, product_type)
            
            # 점수 기준 정렬
            sorted_products = sorted(scored_products, key=lambda x: x["score"], reverse=True)
            
            # 상위 N개 반환
            return [p["product"] for p in sorted_products[:limit]]
            
        except Exception as e:
            logger.error(f"상품 추천 중 오류 발생: {str(e)}")
            return []
    
    async def _get_products(self, product_type: str) -> List[Dict[str, Any]]:
        """
        상품 목록 조회
        
        Args:
            product_type: 상품 유형
            
        Returns:
            상품 목록
        """
        try:
            # DB 연결이 있는 경우 DB에서 조회
            if self.db:
                collection_name = f"{product_type}_products"
                cursor = self.db[collection_name].find({})
                return await cursor.to_list(length=100)
            else:
                # DB 연결이 없는 경우 샘플 데이터 반환
                return self._get_sample_products(product_type)
                
        except Exception as e:
            logger.error(f"상품 목록 조회 실패: {str(e)}")
            return self._get_sample_products(product_type)
    
    def _score_products(
        self, 
        products: List[Dict[str, Any]], 
        user_data: Dict[str, Any], 
        emotion_data: Dict[str, Any],
        product_type: str
    ) -> List[Dict[str, Any]]:
        """
        사용자 데이터를 바탕으로 상품 점수 계산
        
        Args:
            products: 상품 목록
            user_data: 사용자 재무 데이터
            emotion_data: 감정 분석 결과
            product_type: 상품 유형
            
        Returns:
            점수가 매겨진 상품 목록
        """
        scored_products = []
        
        # 감정 상태
        is_negative = emotion_data.get("is_negative", False)
        is_anxious = emotion_data.get("is_anxious", False)
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        
        # 사용자 데이터
        age = user_data.get("age", 35)
        balance = user_data.get("balance_b0m", 0)
        is_delinquent = user_data.get("is_delinquent", False)
        
        for product in products:
            score = 50  # 기본 점수
            
            # 상품 유형별 점수 계산
            if product_type == PRODUCT_TYPE_DEPOSIT:
                score = self._score_deposit_product(product, user_data, emotion_data)
            elif product_type == PRODUCT_TYPE_FUND:
                score = self._score_fund_product(product, user_data, emotion_data)
            
            scored_products.append({
                "product": product,
                "score": score
            })
            
        return scored_products
    
    def _score_deposit_product(
        self, 
        product: Dict[str, Any], 
        user_data: Dict[str, Any], 
        emotion_data: Dict[str, Any]
    ) -> float:
        """
        예금/적금 상품 점수 계산
        
        Args:
            product: 상품 정보
            user_data: 사용자 재무 데이터
            emotion_data: 감정 분석 결과
            
        Returns:
            상품 점수
        """
        score = 50  # 기본 점수
        
        # 감정 상태
        is_negative = emotion_data.get("is_negative", False)
        is_anxious = emotion_data.get("is_anxious", False)
        
        # 사용자 데이터
        age = user_data.get("age", 35)
        balance = user_data.get("balance_b0m", 0)
        is_delinquent = user_data.get("is_delinquent", False)
        
        # 상품 데이터
        interest_rate = product.get("interest_rate", 0)
        min_balance = product.get("min_balance", 0)
        max_term = product.get("max_term", 12)
        product_type = product.get("product_type", "")
        
        # 기본 점수 계산
        
        # 1. 이자율 점수
        score += interest_rate * 10  # 이자율이 높을수록 점수 증가
        
        # 2. 최소 잔액 점수
        if balance >= min_balance:
            score += 10
        else:
            score -= 20
        
        # 3. 상품 유형 점수
        if is_anxious and "안정" in product_type:
            score += 15
        
        # 4. 연령 점수
        if age < 30 and "청년" in product_type:
            score += 10
        elif age >= 50 and "시니어" in product_type:
            score += 10
        
        # 5. 연체 상태 점수
        if is_delinquent and "연체자" in product_type:
            score += 20
        
        # 감정 상태에 따른 조정
        if is_negative:
            if "안정" in product_type:
                score += 10
        
        return max(0, min(100, score))
    
    def _score_fund_product(
        self, 
        product: Dict[str, Any], 
        user_data: Dict[str, Any], 
        emotion_data: Dict[str, Any]
    ) -> float:
        """
        펀드 상품 점수 계산
        
        Args:
            product: 상품 정보
            user_data: 사용자 재무 데이터
            emotion_data: 감정 분석 결과
            
        Returns:
            상품 점수
        """
        score = 50  # 기본 점수
        
        # 감정 상태
        is_negative = emotion_data.get("is_negative", False)
        is_anxious = emotion_data.get("is_anxious", False)
        
        # 사용자 데이터
        age = user_data.get("age", 35)
        balance = user_data.get("balance_b0m", 0)
        is_delinquent = user_data.get("is_delinquent", False)
        
        # 상품 데이터
        expected_return = product.get("expected_return", 0)
        risk_level = product.get("risk_level", 3)
        min_investment = product.get("min_investment", 0)
        fund_type = product.get("fund_type", "")
        
        # 기본 점수 계산
        
        # 1. 수익률 점수
        score += expected_return * 5  # 수익률이 높을수록 점수 증가
        
        # 2. 위험 수준 점수
        if is_anxious:
            score -= risk_level * 5  # 불안 상태에서는 위험 수준이 높을수록 점수 감소
        else:
            score += (6 - risk_level) * 5  # 일반적으로는 위험 수준이 낮을수록 점수 증가
        
        # 3. 최소 투자금 점수
        if balance >= min_investment:
            score += 10
        else:
            score -= 20
        
        # 4. 펀드 유형 점수
        if is_anxious and "안정" in fund_type:
            score += 15
        elif not is_anxious and "성장" in fund_type:
            score += 10
        
        # 5. 연령 점수
        if age < 30 and risk_level >= 4:
            score += 5  # 젊은 층은 위험 수준이 높은 펀드에 적합
        elif age >= 50 and risk_level <= 2:
            score += 5  # 고령층은 위험 수준이 낮은 펀드에 적합
        
        # 감정 상태에 따른 조정
        if is_negative or is_anxious:
            score -= risk_level * 3  # 부정적/불안 감정 상태에서는 위험 수준에 더 민감
        
        return max(0, min(100, score))
    
    def _get_sample_products(self, product_type: str) -> List[Dict[str, Any]]:
        """
        샘플 상품 목록 반환
        
        Args:
            product_type: 상품 유형
            
        Returns:
            샘플 상품 목록
        """
        if product_type == PRODUCT_TYPE_DEPOSIT:
            return [
                {
                    "id": "dp001",
                    "name": "슈퍼 정기예금",
                    "bank": "행복은행",
                    "product_type": "정기예금",
                    "interest_rate": 3.5,
                    "max_interest_rate": 4.0,
                    "min_balance": 100000,
                    "max_term": 12,
                    "description": "12개월 기준 연 3.5% 금리의 정기예금 상품입니다."
                },
                {
                    "id": "dp002",
                    "name": "청년 희망 적금",
                    "bank": "미래은행",
                    "product_type": "청년적금",
                    "interest_rate": 4.0,
                    "max_interest_rate": 4.5,
                    "min_balance": 50000,
                    "max_term": 24,
                    "description": "만 19-34세 청년을 위한 고금리 적금 상품입니다."
                },
                {
                    "id": "dp003",
                    "name": "안심 예금",
                    "bank": "안전은행",
                    "product_type": "안정예금",
                    "interest_rate": 3.0,
                    "max_interest_rate": 3.2,
                    "min_balance": 10000,
                    "max_term": 6,
                    "description": "단기간 안정적인 수익을 원하는 고객을 위한 예금 상품입니다."
                }
            ]
        elif product_type == PRODUCT_TYPE_FUND:
            return [
                {
                    "id": "fd001",
                    "name": "글로벌 성장 펀드",
                    "company": "성장자산운용",
                    "fund_type": "글로벌주식형",
                    "expected_return": 8.5,
                    "risk_level": 4,
                    "min_investment": 1000000,
                    "description": "글로벌 주식에 투자하는 고수익 추구형 펀드입니다."
                },
                {
                    "id": "fd002",
                    "name": "안정 혼합형 펀드",
                    "company": "안정자산운용",
                    "fund_type": "안정혼합형",
                    "expected_return": 5.0,
                    "risk_level": 2,
                    "min_investment": 500000,
                    "description": "채권 위주의 안정적인 수익을 추구하는 혼합형 펀드입니다."
                },
                {
                    "id": "fd003",
                    "name": "배당 플러스 펀드",
                    "company": "배당자산운용",
                    "fund_type": "배당주식형",
                    "expected_return": 6.5,
                    "risk_level": 3,
                    "min_investment": 300000,
                    "description": "배당수익률이 높은 기업에 투자하는 중위험 펀드입니다."
                }
            ]
        else:
            return []

# 싱글톤 인스턴스
_product_matcher = None

def get_product_matcher(db_client=None) -> ProductMatcher:
    """금융상품 매칭 엔진 싱글톤 인스턴스 반환"""
    global _product_matcher
    if _product_matcher is None:
        _product_matcher = ProductMatcher(db_client)
    return _product_matcher

# 기존 코드와의 호환성을 위한 함수들
async def recommend_deposit_products(
    user_id: str, 
    user_data: Dict[str, Any], 
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """예금/적금 상품 추천 (호환성 함수)"""
    matcher = get_product_matcher()
    return await matcher.recommend_products(user_id, user_data, emotion_data, PRODUCT_TYPE_DEPOSIT, limit)

async def recommend_fund_products(
    user_id: str, 
    user_data: Dict[str, Any], 
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """펀드 상품 추천 (호환성 함수)"""
    matcher = get_product_matcher()
    return await matcher.recommend_products(user_id, user_data, emotion_data, PRODUCT_TYPE_FUND, limit)
