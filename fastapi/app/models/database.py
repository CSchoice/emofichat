"""
데이터베이스 모델 정의

MySQL 데이터베이스 테이블 구조를 정의합니다.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """사용자 정보 테이블"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    emotions = relationship("EmotionRecord", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    financial_profiles = relationship("FinancialProfile", back_populates="user")


class EmotionRecord(Base):
    """감정 기록 테이블"""
    __tablename__ = "emotion_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    message = Column(Text, nullable=False)
    dominant_emotion = Column(String(50), nullable=False)
    dominant_score = Column(Float, nullable=False)
    is_negative = Column(Boolean, default=False)
    is_anxious = Column(Boolean, default=False)
    all_emotions = Column(JSON, nullable=True)  # 모든 감정 점수를 JSON으로 저장
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # 관계 설정
    user = relationship("User", back_populates="emotions")


class Conversation(Base):
    """대화 기록 테이블"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    session_id = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # 관계 설정
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """메시지 테이블"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    is_user = Column(Boolean, default=True)  # True: 사용자 메시지, False: 시스템 응답
    content = Column(Text, nullable=False)
    emotion_record_id = Column(Integer, ForeignKey("emotion_records.id"), nullable=True)
    state = Column(String(50), nullable=True)  # 대화 상태
    sent_at = Column(DateTime, default=datetime.utcnow)

    # 관계 설정
    conversation = relationship("Conversation", back_populates="messages")
    emotion_record = relationship("EmotionRecord")


class FinancialProfile(Base):
    """재무 프로필 테이블"""
    __tablename__ = "financial_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False, unique=True)
    income = Column(Float, nullable=True)
    expenses = Column(Float, nullable=True)
    savings = Column(Float, nullable=True)
    debt = Column(Float, nullable=True)
    risk_tolerance = Column(String(20), nullable=True)  # 'low', 'medium', 'high'
    financial_goals = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    user = relationship("User", back_populates="financial_profiles")
    risk_evaluations = relationship("RiskEvaluation", back_populates="financial_profile")


class RiskEvaluation(Base):
    """위험 평가 테이블"""
    __tablename__ = "risk_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    financial_profile_id = Column(Integer, ForeignKey("financial_profiles.id"), nullable=False)
    financial_stress_index = Column(Float, nullable=False)
    stress_trend = Column(String(20), nullable=True)  # 'increasing', 'stable', 'decreasing'
    evaluation_factors = Column(JSON, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    # 관계 설정
    financial_profile = relationship("FinancialProfile", back_populates="risk_evaluations")


class Product(Base):
    """금융 상품 테이블"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 'deposit', 'fund', 등
    description = Column(Text, nullable=True)
    interest_rate = Column(Float, nullable=True)
    min_period = Column(Integer, nullable=True)  # 최소 가입 기간(월)
    max_period = Column(Integer, nullable=True)  # 최대 가입 기간(월)
    min_amount = Column(Float, nullable=True)  # 최소 가입 금액
    risk_level = Column(String(20), nullable=True)  # 'low', 'medium', 'high'
    features = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    recommendations = relationship("Recommendation", back_populates="product")


class Recommendation(Base):
    """추천 기록 테이블"""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    score = Column(Float, nullable=False)  # 추천 점수
    explanation = Column(Text, nullable=True)  # 추천 이유
    recommended_at = Column(DateTime, default=datetime.utcnow)
    is_clicked = Column(Boolean, default=False)  # 사용자가 추천을 클릭했는지 여부
    clicked_at = Column(DateTime, nullable=True)

    # 관계 설정
    user = relationship("User")
    product = relationship("Product", back_populates="recommendations")
    conversation = relationship("Conversation")
