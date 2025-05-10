"""
추천 결과 포맷터

추천된 금융상품과 설명을 사용자에게 보여주기 좋은 형태로 포맷팅합니다.
"""

import logging
from typing import Dict, Any, List, Optional

# 로거 설정
logger = logging.getLogger(__name__)

# 상품 유형 상수
PRODUCT_TYPE_DEPOSIT = "deposit"  # 예금/적금
PRODUCT_TYPE_FUND = "fund"       # 펀드

class RecommendationFormatter:
    """추천 결과 포맷팅 클래스"""
    
    def format_recommendation(
        self, 
        products: List[Dict[str, Any]], 
        product_type: str, 
        emotion_data: Dict[str, Any] = None
    ) -> str:
        """
        추천 결과 포맷팅
        
        Args:
            products: 추천된 상품 목록
            product_type: 상품 유형
            emotion_data: 감정 분석 결과 (선택적)
            
        Returns:
            포맷팅된 추천 결과
        """
        try:
            # 추천 상품이 없는 경우
            if not products:
                return self._format_empty_recommendation(product_type, emotion_data)
                
            # 상품 유형별 포맷팅
            if product_type == PRODUCT_TYPE_DEPOSIT:
                return self._format_deposit_recommendation(products, emotion_data)
            elif product_type == PRODUCT_TYPE_FUND:
                return self._format_fund_recommendation(products, emotion_data)
            else:
                return self._format_empty_recommendation(product_type, emotion_data)
                
        except Exception as e:
            logger.error(f"추천 결과 포맷팅 중 오류 발생: {str(e)}")
            return "추천 결과를 표시하는 중 오류가 발생했습니다."
    
    def _format_deposit_recommendation(
        self, 
        products: List[Dict[str, Any]], 
        emotion_data: Dict[str, Any] = None
    ) -> str:
        """
        예금/적금 추천 결과 포맷팅
        
        Args:
            products: 추천된 상품 목록
            emotion_data: 감정 분석 결과 (선택적)
            
        Returns:
            포맷팅된 추천 결과
        """
        # 감정 상태에 따른 인사말
        greeting = self._get_emotion_greeting(emotion_data)
        
        # 추천 결과 헤더
        result = f"{greeting}\n\n📌 **예금/적금 상품 추천**\n\n"
        
        # 추천 상품 목록
        for i, product in enumerate(products):
            # 상품 기본 정보
            name = product.get("name", "")
            bank = product.get("bank", "")
            product_type = product.get("product_type", "")
            interest_rate = product.get("interest_rate", 0)
            max_interest_rate = product.get("max_interest_rate", 0)
            min_balance = product.get("min_balance", 0)
            max_term = product.get("max_term", 12)
            
            # 상품 설명
            description = product.get("description", "")
            
            # 추천 근거 (있는 경우)
            explanation = ""
            if "explanation" in product:
                exp = product["explanation"]
                matching_factors = exp.get("matching_factors", [])
                emotion_factors = exp.get("emotion_factors", [])
                
                if matching_factors or emotion_factors:
                    explanation = "\n   - 추천 이유: "
                    
                    if matching_factors:
                        explanation += f"{matching_factors[0]}"
                        
                    if emotion_factors:
                        if matching_factors:
                            explanation += f", {emotion_factors[0]}"
                        else:
                            explanation += f"{emotion_factors[0]}"
            
            # 상품 정보 포맷팅
            result += f"{i+1}. **{name}** ({bank})\n"
            result += f"   - 상품유형: {product_type}\n"
            result += f"   - 기본금리: {interest_rate}%"
            
            # 우대금리가 있는 경우
            if max_interest_rate > interest_rate:
                result += f" (최대 {max_interest_rate}%)\n"
            else:
                result += "\n"
                
            result += f"   - 계약기간: {max_term}개월\n"
            result += f"   - 가입금액: {min_balance:,}원 이상"
            
            # 추천 근거 추가
            result += f"{explanation}\n\n"
        
        # 안내 문구
        result += "해당 상품에 관심이 있으시면 자세한 상담을 도와드리겠습니다. 어떤 상품이 가장 마음에 드시나요?"
        
        return result
    
    def _format_fund_recommendation(
        self, 
        products: List[Dict[str, Any]], 
        emotion_data: Dict[str, Any] = None
    ) -> str:
        """
        펀드 추천 결과 포맷팅
        
        Args:
            products: 추천된 상품 목록
            emotion_data: 감정 분석 결과 (선택적)
            
        Returns:
            포맷팅된 추천 결과
        """
        # 감정 상태에 따른 인사말
        greeting = self._get_emotion_greeting(emotion_data)
        
        # 추천 결과 헤더
        result = f"{greeting}\n\n📌 **펀드 상품 추천**\n\n"
        
        # 추천 상품 목록
        for i, product in enumerate(products):
            # 상품 기본 정보
            name = product.get("name", "")
            company = product.get("company", "")
            fund_type = product.get("fund_type", "")
            expected_return = product.get("expected_return", 0)
            risk_level = product.get("risk_level", 3)
            min_investment = product.get("min_investment", 0)
            
            # 위험 수준 텍스트
            risk_text = ["매우 낮음", "낮음", "보통", "높음", "매우 높음"]
            risk_display = risk_text[risk_level-1] if 1 <= risk_level <= 5 else "보통"
            
            # 상품 설명
            description = product.get("description", "")
            
            # 추천 근거 (있는 경우)
            explanation = ""
            if "explanation" in product:
                exp = product["explanation"]
                matching_factors = exp.get("matching_factors", [])
                emotion_factors = exp.get("emotion_factors", [])
                
                if matching_factors or emotion_factors:
                    explanation = "\n   - 추천 이유: "
                    
                    if matching_factors:
                        explanation += f"{matching_factors[0]}"
                        
                    if emotion_factors:
                        if matching_factors:
                            explanation += f", {emotion_factors[0]}"
                        else:
                            explanation += f"{emotion_factors[0]}"
            
            # 상품 정보 포맷팅
            result += f"{i+1}. **{name}** ({company})\n"
            result += f"   - 유형: {fund_type}\n"
            result += f"   - 수익률: 연 {expected_return}% (예상)\n"
            result += f"   - 위험등급: {risk_display}\n"
            result += f"   - 최소투자금액: {min_investment:,}원"
            
            # 추천 근거 추가
            result += f"{explanation}\n\n"
        
        # 안내 문구
        result += "해당 상품에 관심이 있으시면 자세한 상담을 도와드리겠습니다. 어떤 상품이 가장 마음에 드시나요?"
        
        return result
    
    def _format_empty_recommendation(
        self, 
        product_type: str, 
        emotion_data: Dict[str, Any] = None
    ) -> str:
        """
        추천 상품이 없는 경우 포맷팅
        
        Args:
            product_type: 상품 유형
            emotion_data: 감정 분석 결과 (선택적)
            
        Returns:
            포맷팅된 추천 결과
        """
        # 감정 상태에 따른 인사말
        greeting = self._get_emotion_greeting(emotion_data)
        
        # 상품 유형별 메시지
        if product_type == PRODUCT_TYPE_DEPOSIT:
            message = "현재 조건에 맞는 예금/적금 상품을 찾지 못했습니다."
        elif product_type == PRODUCT_TYPE_FUND:
            message = "현재 조건에 맞는 펀드 상품을 찾지 못했습니다."
        else:
            message = "현재 조건에 맞는 상품을 찾지 못했습니다."
        
        # 추천 결과 포맷팅
        result = f"{greeting}\n\n{message}\n\n더 자세한 정보를 알려주시면 더 적합한 상품을 추천해 드릴 수 있습니다."
        
        return result
    
    def _get_emotion_greeting(self, emotion_data: Dict[str, Any] = None) -> str:
        """
        감정 상태에 따른 인사말 생성
        
        Args:
            emotion_data: 감정 분석 결과 (선택적)
            
        Returns:
            감정 상태에 따른 인사말
        """
        # 감정 데이터가 없는 경우
        if not emotion_data:
            return "고객님의 요청에 따라 금융 상품을 추천해 드립니다."
            
        # 감정 상태
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        is_negative = emotion_data.get("is_negative", False)
        is_anxious = emotion_data.get("is_anxious", False)
        
        # 감정별 인사말
        if dominant_emotion == "화남":
            return "불편한 상황이신 것 같습니다. 고객님의 상황에 도움이 될 수 있는 금융 상품을 추천해 드립니다."
        elif dominant_emotion == "슬픔":
            return "힘든 상황에서도 재정적인 안정을 찾으실 수 있도록, 고객님께 적합한 금융 상품을 추천해 드립니다."
        elif dominant_emotion == "공포" or dominant_emotion == "걱정":
            return "금융에 대한 걱정이 있으신 것 같습니다. 안정적인 금융 상품을 통해 불안감을 줄이실 수 있습니다."
        elif dominant_emotion == "행복":
            return "좋은 기분을 더욱 높여줄 수 있는 금융 상품을 추천해 드립니다."
        else:
            return "고객님의 요청에 따라 금융 상품을 추천해 드립니다."

# 싱글톤 인스턴스
_recommendation_formatter = None

def get_recommendation_formatter() -> RecommendationFormatter:
    """추천 결과 포맷터 싱글톤 인스턴스 반환"""
    global _recommendation_formatter
    if _recommendation_formatter is None:
        _recommendation_formatter = RecommendationFormatter()
    return _recommendation_formatter

# 기존 코드와의 호환성을 위한 함수
def format_product_recommendation(
    products: List[Dict[str, Any]], 
    product_type: str, 
    emotion_data: Dict[str, Any] = None
) -> str:
    """
    추천 결과 포맷팅 (호환성 함수)
    """
    formatter = get_recommendation_formatter()
    return formatter.format_recommendation(products, product_type, emotion_data)
