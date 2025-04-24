# app/models/finance.py
from sqlalchemy import Column, String, Integer, Float, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FinanceMetric(Base):
    """금융 지표 데이터 ORM 모델"""
    __tablename__ = "finance_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), index=True, nullable=False)
    record_date = Column(Date, nullable=False)
    
    # 카드 사용 지표
    credit_card_count = Column(Integer)
    check_card_count = Column(Integer)
    credit_usage_3m = Column(Float(precision=20, asdecimal=True))
    check_usage_3m = Column(Float(precision=20, asdecimal=True))
    top1_card_usage = Column(Float(precision=20, asdecimal=True))
    top2_card_usage = Column(Float(precision=20, asdecimal=True))
    first_limit_amount = Column(Float(precision=20, asdecimal=True))
    current_limit_amount = Column(Float(precision=20, asdecimal=True))
    ca_limit_amount = Column(Float(precision=20, asdecimal=True))
    
    # 연체 지표
    delinquent_balance_b0m = Column(Float(precision=20, asdecimal=True))
    delinquent_balance_ca_b0m = Column(Float(precision=20, asdecimal=True))
    recent_delinquent_days = Column(Integer)
    max_delinquent_months_r15m = Column(Integer)
    is_delinquent = Column(Integer)  # Boolean으로 처리됨
    limit_down_amount_r12m = Column(Float(precision=20, asdecimal=True))
    limit_up_amount_r12m = Column(Float(precision=20, asdecimal=True))
    limit_up_available = Column(Float(precision=20, asdecimal=True))
    
    # 잔액 정보
    balance_b0m = Column(Float(precision=20, asdecimal=True))
    balance_lump_b0m = Column(Float(precision=20, asdecimal=True))
    balance_loan_b0m = Column(Float(precision=20, asdecimal=True))
    avg_balance_3m = Column(Float(precision=20, asdecimal=True))
    avg_ca_balance_3m = Column(Float(precision=20, asdecimal=True))
    avg_loan_balance_3m = Column(Float(precision=20, asdecimal=True))
    ca_interest_rate = Column(Float(precision=20, asdecimal=True))
    revolving_min_payment_ratio = Column(Float(precision=20, asdecimal=True))
    
    # 소비 패턴
    spending_shopping = Column(Float(precision=20, asdecimal=True))
    spending_food = Column(Float(precision=20, asdecimal=True))
    spending_transport = Column(Float(precision=20, asdecimal=True))
    spending_medical = Column(Float(precision=20, asdecimal=True))
    spending_payment = Column(Float(precision=20, asdecimal=True))
    life_stage = Column(String(20))
    card_application_count = Column(Integer)
    last_card_issued_months_ago = Column(Integer)
    
    # 시나리오 지표
    scenario_labels = Column(String(255))
    dti_estimate = Column(Float)
    spending_change_ratio = Column(Float)
    essential_ratio = Column(Float)
    credit_usage_ratio = Column(Float)
    debt_ratio = Column(Float)
    revolving_dependency = Column(Float)
    necessity_ratio = Column(Float)
    housing_ratio = Column(Float)
    medical_ratio = Column(Float)
    
    def __repr__(self):
        return f"<FinanceMetric(user_id='{self.user_id}', date='{self.record_date}')>"