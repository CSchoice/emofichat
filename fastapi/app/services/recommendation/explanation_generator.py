"""
추천 근거 설명 생성기

추천된 금융상품의 근거를 설명하는 역할을 합니다.
"""

import logging
from typing import Dict, Any, List, Optional

# 로거 설정
logger = logging.getLogger(__name__)

class ExplanationGenerator:
    """추천 근거 설명 생성 클래스"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
    async def generate_explanations(
        self, 
        products: List[Dict[str, Any]], 
        user_data: Dict[str, Any], 
        emotion_data: Dict[str, Any],
        product_type: str
    ) -> List[Dict[str, Any]]:
        """
        추천 상품에 대한 설명 생성
        
        Args:
            products: 추천된 상품 목록
            user_data: 사용자 재무 데이터
            emotion_data: 감정 분석 결과
            product_type: 상품 유형
            
        Returns:
            설명이 추가된 상품 목록
        """
        try:
            explanations = []
            
            for product in products:
                # 1. 제품 특성과 사용자 상황 매칭
                matching_factors = self._identify_matching_factors(product, user_data, product_type)
                
                # 2. 감정 상태 고려 요소
                emotion_factors = self._identify_emotion_factors(product, emotion_data, product_type)
                
                # 3. 설명 생성
                explanation = {
                    "product_id": product.get("id", ""),
                    "product_name": product.get("name", ""),
                    "matching_factors": matching_factors,
                    "emotion_factors": emotion_factors,
                    "risk_assessment": self._assess_risk(product, user_data, product_type),
                    "benefit_summary": self._summarize_benefits(product, product_type),
                    "natural_language_explanation": await self._generate_nl_explanation(
                        product, matching_factors, emotion_factors, user_data, product_type
                    )
                }
                
                # 4. 원본 상품 정보에 설명 추가
                product_with_explanation = {
                    **product,
                    "explanation": explanation
                }
                
                explanations.append(product_with_explanation)
                
            return explanations
            
        except Exception as e:
            logger.error(f"추천 설명 생성 중 오류 발생: {str(e)}")
            return products  # 오류 발생 시 원본 상품 목록 반환
    
    def _identify_matching_factors(
        self, 
        product: Dict[str, Any], 
        user_data: Dict[str, Any],
        product_type: str
    ) -> List[str]:
        """
        제품 특성과 사용자 상황 매칭 요소 식별
        
        Args:
            product: 상품 정보
            user_data: 사용자 재무 데이터
            product_type: 상품 유형
            
        Returns:
            매칭 요소 목록
        """
        factors = []
        
        # 사용자 데이터
        age = user_data.get("age", 35)
        balance = user_data.get("balance_b0m", 0)
        is_delinquent = user_data.get("is_delinquent", False)
        
        # 상품 유형별 매칭 요소 식별
        if product_type == "deposit":  # 예금/적금
            # 상품 데이터
            interest_rate = product.get("interest_rate", 0)
            max_interest_rate = product.get("max_interest_rate", 0)
            min_balance = product.get("min_balance", 0)
            max_term = product.get("max_term", 12)
            product_subtype = product.get("product_type", "")
            
            # 1. 금리 매칭
            if interest_rate >= 3.0:
                factors.append(f"높은 기본금리 {interest_rate}%")
            
            # 2. 우대금리 매칭
            if max_interest_rate > interest_rate:
                factors.append(f"최대 {max_interest_rate}%의 우대금리 적용 가능")
            
            # 3. 최소 잔액 매칭
            if balance >= min_balance:
                factors.append(f"현재 잔액({balance:,}원)으로 가입 가능")
            
            # 4. 연령 매칭
            if "청년" in product_subtype and age < 30:
                factors.append("청년 대상 특화 상품")
            elif "시니어" in product_subtype and age >= 50:
                factors.append("시니어 대상 특화 상품")
            
        elif product_type == "fund":  # 펀드
            # 상품 데이터
            expected_return = product.get("expected_return", 0)
            risk_level = product.get("risk_level", 3)
            min_investment = product.get("min_investment", 0)
            fund_type = product.get("fund_type", "")
            
            # 1. 수익률 매칭
            if expected_return >= 5.0:
                factors.append(f"예상 수익률 {expected_return}%")
            
            # 2. 위험 수준 매칭
            risk_text = ["매우 낮음", "낮음", "보통", "높음", "매우 높음"]
            if risk_level <= 2:
                factors.append(f"안정적인 위험 수준 ({risk_text[risk_level-1]})")
            
            # 3. 최소 투자금 매칭
            if balance >= min_investment:
                factors.append(f"현재 잔액({balance:,}원)으로 투자 가능")
            
            # 4. 연령 매칭
            if age < 30 and risk_level >= 3:
                factors.append("젊은 연령층에 적합한 성장형 상품")
            elif age >= 50 and risk_level <= 2:
                factors.append("장년층에 적합한 안정형 상품")
        
        return factors
    
    def _identify_emotion_factors(
        self, 
        product: Dict[str, Any], 
        emotion_data: Dict[str, Any],
        product_type: str
    ) -> List[str]:
        """
        감정 상태 고려 요소 식별
        
        Args:
            product: 상품 정보
            emotion_data: 감정 분석 결과
            product_type: 상품 유형
            
        Returns:
            감정 고려 요소 목록
        """
        factors = []
        
        # 감정 상태
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        is_negative = emotion_data.get("is_negative", False)
        is_anxious = emotion_data.get("is_anxious", False)
        
        # 상품 유형별 감정 고려 요소 식별
        if product_type == "deposit":  # 예금/적금
            # 상품 데이터
            product_subtype = product.get("product_type", "")
            
            # 1. 불안 감정 대응
            if is_anxious and ("안정" in product_subtype or "정기" in product_subtype):
                factors.append("현재 불안한 감정에 안정감을 줄 수 있는 상품")
            
            # 2. 부정 감정 대응
            if is_negative and "정기" in product_subtype:
                factors.append("예측 가능한 수익으로 안정감 제공")
            
            # 3. 특정 감정 대응
            if dominant_emotion == "걱정" and "적금" in product_subtype:
                factors.append("정기적인 저축으로 재정 걱정 완화")
            elif dominant_emotion == "화남" and product.get("interest_rate", 0) >= 3.0:
                factors.append("높은 금리로 금융 만족도 향상")
            
        elif product_type == "fund":  # 펀드
            # 상품 데이터
            risk_level = product.get("risk_level", 3)
            fund_type = product.get("fund_type", "")
            
            # 1. 불안 감정 대응
            if is_anxious and risk_level <= 2:
                factors.append("낮은 위험도로 불안감 완화")
            
            # 2. 부정 감정 대응
            if is_negative and "안정" in fund_type:
                factors.append("안정적인 투자로 부정적 감정 완화")
            
            # 3. 특정 감정 대응
            if dominant_emotion == "걱정" and "채권" in fund_type:
                factors.append("안정적인 채권형 상품으로 재정 걱정 완화")
            elif dominant_emotion == "화남" and "배당" in fund_type:
                factors.append("정기적인 배당으로 금융 만족도 향상")
        
        return factors
    
    def _assess_risk(
        self, 
        product: Dict[str, Any], 
        user_data: Dict[str, Any],
        product_type: str
    ) -> Dict[str, Any]:
        """
        상품의 위험도 평가
        
        Args:
            product: 상품 정보
            user_data: 사용자 재무 데이터
            product_type: 상품 유형
            
        Returns:
            위험도 평가 결과
        """
        # 기본 결과 구조
        result = {
            "risk_level": "낮음",
            "risk_score": 20,
            "is_suitable": True,
            "risk_factors": [],
            "mitigation_factors": []
        }
        
        # 사용자 데이터
        age = user_data.get("age", 35)
        balance = user_data.get("balance_b0m", 0)
        is_delinquent = user_data.get("is_delinquent", False)
        
        # 상품 유형별 위험도 평가
        if product_type == "deposit":  # 예금/적금
            # 상품 데이터
            min_balance = product.get("min_balance", 0)
            max_term = product.get("max_term", 12)
            
            # 1. 위험 점수 계산 (예금/적금은 기본적으로 위험이 낮음)
            risk_score = 10
            
            # 2. 가입 가능 여부
            if balance < min_balance:
                risk_score += 20
                result["risk_factors"].append(f"최소 가입금액({min_balance:,}원)에 미달")
                result["is_suitable"] = False
            else:
                result["mitigation_factors"].append("충분한 가입금액 보유")
            
            # 3. 연체 상태
            if is_delinquent:
                risk_score += 10
                result["risk_factors"].append("현재 연체 상태로 가입 제한 가능성")
            
            # 4. 만기 기간
            if max_term > 12:
                risk_score += 5
                result["risk_factors"].append(f"비교적 긴 만기 기간({max_term}개월)")
            else:
                result["mitigation_factors"].append("적절한 만기 기간")
            
        elif product_type == "fund":  # 펀드
            # 상품 데이터
            risk_level = product.get("risk_level", 3)
            min_investment = product.get("min_investment", 0)
            
            # 1. 위험 점수 계산 (펀드 자체 위험 수준 반영)
            risk_score = risk_level * 20
            
            # 2. 가입 가능 여부
            if balance < min_investment:
                risk_score += 20
                result["risk_factors"].append(f"최소 투자금액({min_investment:,}원)에 미달")
                result["is_suitable"] = False
            else:
                result["mitigation_factors"].append("충분한 투자금액 보유")
            
            # 3. 연체 상태
            if is_delinquent:
                risk_score += 15
                result["risk_factors"].append("현재 연체 상태로 투자 위험도 증가")
            
            # 4. 연령 고려
            if age >= 60 and risk_level >= 4:
                risk_score += 10
                result["risk_factors"].append("고연령층에 비해 높은 위험 수준")
                result["is_suitable"] = False
            elif age <= 30 and risk_level <= 2:
                result["mitigation_factors"].append("젊은 연령층에 적합한 안정적 상품")
        
        # 위험 점수 범위 조정
        risk_score = max(0, min(100, risk_score))
        result["risk_score"] = risk_score
        
        # 위험 수준 결정
        if risk_score >= 70:
            result["risk_level"] = "매우 높음"
        elif risk_score >= 50:
            result["risk_level"] = "높음"
        elif risk_score >= 30:
            result["risk_level"] = "중간"
        elif risk_score >= 10:
            result["risk_level"] = "낮음"
        else:
            result["risk_level"] = "매우 낮음"
        
        return result
    
    def _summarize_benefits(self, product: Dict[str, Any], product_type: str) -> List[str]:
        """
        상품의 주요 혜택 요약
        
        Args:
            product: 상품 정보
            product_type: 상품 유형
            
        Returns:
            혜택 요약 목록
        """
        benefits = []
        
        # 상품 유형별 혜택 요약
        if product_type == "deposit":  # 예금/적금
            # 상품 데이터
            interest_rate = product.get("interest_rate", 0)
            max_interest_rate = product.get("max_interest_rate", 0)
            max_term = product.get("max_term", 12)
            product_subtype = product.get("product_type", "")
            
            # 1. 금리 혜택
            benefits.append(f"기본 금리 연 {interest_rate}%")
            
            # 2. 우대 금리 혜택
            if max_interest_rate > interest_rate:
                benefits.append(f"최대 우대 금리 연 {max_interest_rate}%")
            
            # 3. 상품 유형별 혜택
            if "정기예금" in product_subtype:
                benefits.append(f"만기 시 원금과 이자 보장")
            elif "적금" in product_subtype:
                benefits.append(f"정기적인 저축으로 자산 형성")
            
            # 4. 기타 혜택
            if max_term <= 6:
                benefits.append(f"단기 {max_term}개월 상품으로 유동성 확보")
            elif max_term >= 24:
                benefits.append(f"장기 {max_term}개월 상품으로 높은 수익률")
            
        elif product_type == "fund":  # 펀드
            # 상품 데이터
            expected_return = product.get("expected_return", 0)
            risk_level = product.get("risk_level", 3)
            fund_type = product.get("fund_type", "")
            
            # 1. 수익률 혜택
            benefits.append(f"예상 수익률 연 {expected_return}%")
            
            # 2. 위험 수준 혜택
            risk_text = ["매우 낮음", "낮음", "보통", "높음", "매우 높음"]
            benefits.append(f"위험 수준: {risk_text[risk_level-1]}")
            
            # 3. 펀드 유형별 혜택
            if "주식" in fund_type:
                benefits.append("주식 투자를 통한 높은 수익 기대")
            elif "채권" in fund_type:
                benefits.append("채권 투자를 통한 안정적 수익")
            elif "혼합" in fund_type:
                benefits.append("주식과 채권 혼합으로 균형 잡힌 포트폴리오")
            elif "배당" in fund_type:
                benefits.append("정기적인 배당 수익 기대")
            
            # 4. 기타 혜택
            if "글로벌" in fund_type:
                benefits.append("글로벌 분산 투자로 위험 분산")
            elif "국내" in fund_type:
                benefits.append("국내 시장 집중 투자")
        
        return benefits
    
    async def _generate_nl_explanation(
        self, 
        product: Dict[str, Any], 
        matching_factors: List[str], 
        emotion_factors: List[str], 
        user_data: Dict[str, Any],
        product_type: str
    ) -> str:
        """
        자연어 설명 생성
        
        Args:
            product: 상품 정보
            matching_factors: 매칭 요소 목록
            emotion_factors: 감정 고려 요소 목록
            user_data: 사용자 재무 데이터
            product_type: 상품 유형
            
        Returns:
            자연어 설명
        """
        try:
            # LLM 클라이언트가 있는 경우 LLM을 사용하여 설명 생성
            if self.llm_client:
                # 프롬프트 구성
                prompt = self._build_explanation_prompt(product, matching_factors, emotion_factors, user_data, product_type)
                
                # LLM 호출
                response = await self.llm_client.generate(prompt)
                return response.text
            else:
                # LLM 클라이언트가 없는 경우 템플릿 기반 설명 생성
                return self._build_template_explanation(product, matching_factors, emotion_factors, product_type)
                
        except Exception as e:
            logger.error(f"자연어 설명 생성 중 오류 발생: {str(e)}")
            return self._build_template_explanation(product, matching_factors, emotion_factors, product_type)
    
    def _build_template_explanation(
        self, 
        product: Dict[str, Any], 
        matching_factors: List[str], 
        emotion_factors: List[str],
        product_type: str
    ) -> str:
        """
        템플릿 기반 설명 생성
        
        Args:
            product: 상품 정보
            matching_factors: 매칭 요소 목록
            emotion_factors: 감정 고려 요소 목록
            product_type: 상품 유형
            
        Returns:
            템플릿 기반 설명
        """
        # 상품 정보
        product_name = product.get("name", "")
        
        # 상품 유형별 설명
        if product_type == "deposit":  # 예금/적금
            bank = product.get("bank", "")
            interest_rate = product.get("interest_rate", 0)
            max_interest_rate = product.get("max_interest_rate", 0)
            
            # 기본 설명
            explanation = f"{bank}의 {product_name} 상품은 기본 금리 연 {interest_rate}%의 상품입니다."
            
            # 우대 금리가 있는 경우
            if max_interest_rate > interest_rate:
                explanation += f" 조건 충족 시 최대 연 {max_interest_rate}%의 우대 금리를 적용받을 수 있습니다."
            
        elif product_type == "fund":  # 펀드
            company = product.get("company", "")
            expected_return = product.get("expected_return", 0)
            risk_level = product.get("risk_level", 3)
            
            # 위험 수준 텍스트
            risk_text = ["매우 낮음", "낮음", "보통", "높음", "매우 높음"]
            
            # 기본 설명
            explanation = f"{company}의 {product_name} 펀드는 예상 수익률 연 {expected_return}%, 위험 수준 {risk_text[risk_level-1]}의 상품입니다."
        
        # 매칭 요소 추가
        if matching_factors:
            explanation += f"\n\n이 상품은 다음과 같은 이유로 추천됩니다:\n"
            for factor in matching_factors:
                explanation += f"- {factor}\n"
        
        # 감정 고려 요소 추가
        if emotion_factors:
            explanation += f"\n현재 감정 상태를 고려한 추천 이유:\n"
            for factor in emotion_factors:
                explanation += f"- {factor}\n"
        
        return explanation
    
    def _build_explanation_prompt(
        self, 
        product: Dict[str, Any], 
        matching_factors: List[str], 
        emotion_factors: List[str], 
        user_data: Dict[str, Any],
        product_type: str
    ) -> str:
        """
        LLM용 설명 생성 프롬프트 구성
        
        Args:
            product: 상품 정보
            matching_factors: 매칭 요소 목록
            emotion_factors: 감정 고려 요소 목록
            user_data: 사용자 재무 데이터
            product_type: 상품 유형
            
        Returns:
            LLM 프롬프트
        """
        # 상품 정보 JSON 형식으로 변환
        product_info = "\n".join([f"{k}: {v}" for k, v in product.items()])
        
        # 매칭 요소 목록
        matching_factors_text = "\n".join([f"- {factor}" for factor in matching_factors])
        
        # 감정 고려 요소 목록
        emotion_factors_text = "\n".join([f"- {factor}" for factor in emotion_factors])
        
        # 사용자 데이터
        user_info = "\n".join([f"{k}: {v}" for k, v in user_data.items() if k in ["age", "balance_b0m", "is_delinquent"]])
        
        # 프롬프트 템플릿
        prompt = f"""
        당신은 금융 상품 추천 시스템의 설명 생성기입니다. 다음 정보를 바탕으로 사용자에게 추천된 금융 상품에 대한 자연스러운 설명을 생성해주세요.
        
        ## 상품 정보
        {product_info}
        
        ## 상품 유형
        {product_type}
        
        ## 사용자 정보
        {user_info}
        
        ## 추천 이유
        {matching_factors_text}
        
        ## 감정 고려 요소
        {emotion_factors_text}
        
        다음 형식으로 설명을 생성해주세요:
        1. 상품 소개 (1-2문장)
        2. 이 상품이 사용자에게 적합한 이유 (2-3문장)
        3. 현재 감정 상태를 고려한 추천 이유 (1-2문장)
        4. 상품 활용 제안 (1문장)
        
        자연스러운 대화체로 작성해주세요. 전문 용어는 최소화하고, 쉽게 이해할 수 있는 표현을 사용하세요.
        """
        
        return prompt

# 싱글톤 인스턴스
_explanation_generator = None

def get_explanation_generator(llm_client=None) -> ExplanationGenerator:
    """설명 생성기 싱글톤 인스턴스 반환"""
    global _explanation_generator
    if _explanation_generator is None:
        _explanation_generator = ExplanationGenerator(llm_client)
    return _explanation_generator
