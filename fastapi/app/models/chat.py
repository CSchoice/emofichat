"""
채팅 관련 모델 클래스
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    user_id: str = Field(..., description="사용자 ID")
    message: str = Field(..., description="사용자 메시지")

class EmotionResult(BaseModel):
    """감정 분석 결과 모델"""
    dominant_emotion: str = Field(..., description="주요 감정")
    dominant_score: float = Field(..., description="주요 감정 점수")
    is_negative: bool = Field(..., description="부정적 감정 여부")
    is_anxious: bool = Field(..., description="불안 감정 여부")
    all_emotions: Dict[str, float] = Field(..., description="모든 감정 점수")

class ScenarioResult(BaseModel):
    """시나리오 분석 결과 모델"""
    label: str = Field(..., description="시나리오 라벨")
    probability: float = Field(..., description="시나리오 확률")
    key_metrics: Dict[str, Any] = Field(..., description="주요 지표")

class ProductRecommendation(BaseModel):
    """상품 추천 결과 모델"""
    product_type: str = Field(..., description="상품 유형")
    products: List[Dict[str, Any]] = Field(..., description="추천 상품 목록")

class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    reply: str = Field(..., description="응답 메시지")
    emotion: Optional[EmotionResult] = Field(None, description="감정 분석 결과")
    scenario: Optional[ScenarioResult] = Field(None, description="시나리오 분석 결과")
    product_recommendation: Optional[ProductRecommendation] = Field(None, description="상품 추천 결과")
