# app/models/__init__.py
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ScenarioResult(BaseModel):
    label: str
    probability: float
    key_metrics: Dict[str, str]

class EmotionResult(BaseModel):
    dominant_emotion: str
    dominant_score: float
    is_negative: bool
    is_anxious: bool
    all_emotions: Dict[str, float]

class ProductRecommendation(BaseModel):
    product_type: str  # "deposit" 또는 "fund"
    products: List[Dict]  # 추천 상품 목록

class ChatResponse(BaseModel):
    reply: str
    scenario: Optional[ScenarioResult] = None
    emotion: Optional[EmotionResult] = None
    product_recommendation: Optional[ProductRecommendation] = None

# 감정 트렌드 분석 결과 모델
class EmotionTrendsResponse(BaseModel):
    user_id: str
    days: int
    most_frequent_emotion: str
    emotion_frequency: Dict[str, int]
    avg_emotion_scores: Dict[str, float]
    negative_ratio: float = 0.0
    anxious_ratio: float = 0.0
    emotion_volatility: float = 0.0
    financial_stress_index: float
    stress_trend: str
    data_points: int = 0
    recommendations: List[str] = []

# 금융 건강 상태 응답 모델
class FinancialHealthResponse(BaseModel):
    user_id: str
    financial_stress_index: float
    stress_trend: str
    most_frequent_emotion: str
    emotion_volatility: float = 0.0
    negative_ratio: float = 0.0
    summary: str
    recommendations: List[str] = []
    generated_at: str