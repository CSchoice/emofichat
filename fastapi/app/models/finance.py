from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    """사용자 기본 정보"""
    __tablename__ = "User"

    user_id = Column(String(20), primary_key=True)
    gender = Column(String(10))
    age = Column(Integer)
    residence = Column(String(20))
    workplace = Column(String(20))
    marketing_agree = Column(Integer)
    
    # 관계 정의
    card_usages = relationship("CardUsage", back_populates="user")
    delinquencies = relationship("Delinquency", back_populates="user")
    balance_infos = relationship("BalanceInfo", back_populates="user")
    spending_patterns = relationship("SpendingPattern", back_populates="user")
    scenario_labels = relationship("ScenarioLabel", back_populates="user")

class CardUsage(Base):
    """카드 사용 정보"""
    __tablename__ = "CardUsage"

    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(Date, primary_key=True)
    credit_card_count = Column(Integer)
    check_card_count = Column(Integer)
    credit_usage_3m = Column(Float(precision=20, asdecimal=True))
    check_usage_3m = Column(Float(precision=20, asdecimal=True))
    top1_card_usage = Column(Float(precision=20, asdecimal=True))
    top2_card_usage = Column(Float(precision=20, asdecimal=True))
    first_limit_amount = Column(Float(precision=20, asdecimal=True))
    current_limit_amount = Column(Float(precision=20, asdecimal=True))
    ca_limit_amount = Column(Float(precision=20, asdecimal=True))
    
    # 관계 정의
    user = relationship("User", back_populates="card_usages")

class Delinquency(Base):
    """연체 정보"""
    __tablename__ = "Delinquency"

    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(Date, primary_key=True)
    delinquent_balance_b0m = Column(Float(precision=20, asdecimal=True))
    delinquent_balance_ca_b0m = Column(Float(precision=20, asdecimal=True))
    recent_delinquent_days = Column(Integer)
    max_delinquent_months_r15m = Column(Integer)
    is_delinquent = Column(Integer)
    limit_down_amount_r12m = Column(Float(precision=20, asdecimal=True))
    limit_up_amount_r12m = Column(Float(precision=20, asdecimal=True))
    limit_up_available = Column(Float(precision=20, asdecimal=True))
    
    # 관계 정의
    user = relationship("User", back_populates="delinquencies")

class BalanceInfo(Base):
    """잔액 정보"""
    __tablename__ = "BalanceInfo"

    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(Date, primary_key=True)
    balance_b0m = Column(Float(precision=20, asdecimal=True))
    balance_lump_b0m = Column(Float(precision=20, asdecimal=True))
    balance_loan_b0m = Column(Float(precision=20, asdecimal=True))
    avg_balance_3m = Column(Float(precision=20, asdecimal=True))
    avg_ca_balance_3m = Column(Float(precision=20, asdecimal=True))
    avg_loan_balance_3m = Column(Float(precision=20, asdecimal=True))
    ca_interest_rate = Column(Float(precision=20, asdecimal=True))
    revolving_min_payment_ratio = Column(Float(precision=20, asdecimal=True))
    
    # 관계 정의
    user = relationship("User", back_populates="balance_infos")

class SpendingPattern(Base):
    """소비 패턴 정보"""
    __tablename__ = "SpendingPattern"

    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(Date, primary_key=True)
    spending_shopping = Column(Float(precision=20, asdecimal=True))
    spending_food = Column(Float(precision=20, asdecimal=True))
    spending_transport = Column(Float(precision=20, asdecimal=True))
    spending_medical = Column(Float(precision=20, asdecimal=True))
    spending_payment = Column(Float(precision=20, asdecimal=True))
    life_stage = Column(String(20))
    card_application_count = Column(Integer)
    last_card_issued_months_ago = Column(Integer)
    
    # 관계 정의
    user = relationship("User", back_populates="spending_patterns")

class ScenarioLabel(Base):
    """시나리오 라벨 정보"""
    __tablename__ = "ScenarioLabel"

    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(Date, primary_key=True)
    scenario_labels = Column(String(255))
    dti_estimate = Column(Float(precision=20, asdecimal=True))
    spending_change_ratio = Column(Float(precision=20, asdecimal=True))
    essential_ratio = Column(Float(precision=20, asdecimal=True))
    credit_usage_ratio = Column(Float(precision=20, asdecimal=True))
    debt_ratio = Column(Float(precision=20, asdecimal=True))
    revolving_dependency = Column(Float(precision=20, asdecimal=True))
    necessity_ratio = Column(Float(precision=20, asdecimal=True))
    housing_ratio = Column(Float(precision=20, asdecimal=True))
    medical_ratio = Column(Float(precision=20, asdecimal=True))
    
    # 관계 정의
    user = relationship("User", back_populates="scenario_labels")

# 별칭 정의 - 기존 코드와의 호환성을 위해
FinanceMetric = User
