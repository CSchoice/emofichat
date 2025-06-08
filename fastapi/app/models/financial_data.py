"""
금융 데이터 모델

사용자의 금융 데이터와 금융 상품 정보를 위한 모델 정의
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date, Text, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.db import Base


class User(Base):
    __tablename__ = "User"
    
    user_id = Column(String(20), primary_key=True)
    gender = Column(Integer, nullable=True)
    age = Column(Integer, nullable=True)
    residence = Column(String(20), nullable=True)
    workplace = Column(String(20), nullable=True)
    marketing_agree = Column(String(1), nullable=True)
    
    # 관계 정의
    balance_info = relationship("BalanceInfo", back_populates="user")
    card_usage = relationship("CardUsage", back_populates="user")
    delinquency = relationship("Delinquency", back_populates="user")
    scenario_label = relationship("ScenarioLabel", back_populates="user")
    spending_pattern = relationship("SpendingPattern", back_populates="user")


class BalanceInfo(Base):
    __tablename__ = "BalanceInfo"
    
    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(String(7), primary_key=True)
    balance_b0m = Column(DECIMAL(20, 4), nullable=True)
    balance_lump_b0m = Column(DECIMAL(20, 4), nullable=True)
    balance_loan_b0m = Column(DECIMAL(20, 4), nullable=True)
    avg_balance_3m = Column(DECIMAL(20, 4), nullable=True)
    avg_ca_balance_3m = Column(DECIMAL(20, 4), nullable=True)
    avg_loan_balance_3m = Column(DECIMAL(20, 4), nullable=True)
    ca_interest_rate = Column(DECIMAL(20, 4), nullable=True)
    revolving_min_payment_ratio = Column(DECIMAL(20, 4), nullable=True)
    
    # 관계 정의
    user = relationship("User", back_populates="balance_info")


class CardUsage(Base):
    __tablename__ = "CardUsage"
    
    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(String(7), primary_key=True)
    credit_card_count = Column(Integer, nullable=True)
    check_card_count = Column(Integer, nullable=True)
    credit_usage_3m = Column(DECIMAL(20, 4), nullable=True)
    check_usage_3m = Column(DECIMAL(20, 4), nullable=True)
    top1_card_usage = Column(DECIMAL(20, 4), nullable=True)
    top2_card_usage = Column(DECIMAL(20, 4), nullable=True)
    first_limit_amount = Column(DECIMAL(20, 4), nullable=True)
    current_limit_amount = Column(DECIMAL(20, 4), nullable=True)
    ca_limit_amount = Column(DECIMAL(20, 4), nullable=True)
    
    # 관계 정의
    user = relationship("User", back_populates="card_usage")


class Delinquency(Base):
    __tablename__ = "Delinquency"
    
    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(String(7), primary_key=True)
    delinquent_balance_b0m = Column(DECIMAL(20, 4), nullable=True)
    delinquent_balance_ca_b0m = Column(DECIMAL(20, 4), nullable=True)
    recent_delinquent_days = Column(Integer, nullable=True)
    max_delinquent_months_r15m = Column(Integer, nullable=True)
    is_delinquent = Column(String(1), nullable=True)
    limit_down_amount_r12m = Column(DECIMAL(20, 4), nullable=True)
    limit_up_amount_r12m = Column(DECIMAL(20, 4), nullable=True)
    limit_up_available = Column(DECIMAL(20, 4), nullable=True)
    
    # 관계 정의
    user = relationship("User", back_populates="delinquency")


class ScenarioLabel(Base):
    __tablename__ = "ScenarioLabel"
    
    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(String(7), primary_key=True)
    scenario_labels = Column(String(100), nullable=True)
    dti_estimate = Column(DECIMAL(20, 4), nullable=True)
    spending_change_ratio = Column(DECIMAL(20, 4), nullable=True)
    essential_ratio = Column(DECIMAL(20, 4), nullable=True)
    credit_usage_ratio = Column(DECIMAL(20, 4), nullable=True)
    debt_ratio = Column(DECIMAL(20, 4), nullable=True)
    revolving_dependency = Column(DECIMAL(20, 4), nullable=True)
    necessity_ratio = Column(DECIMAL(20, 4), nullable=True)
    housing_ratio = Column(DECIMAL(20, 4), nullable=True)
    medical_ratio = Column(DECIMAL(20, 4), nullable=True)
    
    # 관계 정의
    user = relationship("User", back_populates="scenario_label")


class SpendingPattern(Base):
    __tablename__ = "SpendingPattern"
    
    user_id = Column(String(20), ForeignKey("User.user_id"), primary_key=True)
    record_date = Column(String(7), primary_key=True)
    spending_shopping = Column(DECIMAL(20, 4), nullable=True)
    spending_food = Column(DECIMAL(20, 4), nullable=True)
    spending_transport = Column(DECIMAL(20, 4), nullable=True)
    spending_medical = Column(DECIMAL(20, 4), nullable=True)
    spending_payment = Column(DECIMAL(20, 4), nullable=True)
    life_stage = Column(String(20), nullable=True)
    card_application_count = Column(Integer, nullable=True)
    last_card_issued_months_ago = Column(Integer, nullable=True)
    
    # 관계 정의
    user = relationship("User", back_populates="spending_pattern")


class Bank(Base):
    __tablename__ = "bank"
    
    bank_id = Column(Integer, primary_key=True, autoincrement=True)
    bank_name = Column(String(255), unique=True)
    
    # 관계 정의
    products = relationship("BankProduct", back_populates="bank")


class BankCompany(Base):
    __tablename__ = "bank_company"
    
    fin_co_no = Column(String(20), primary_key=True)
    kor_co_nm = Column(String(200), nullable=True)
    
    # 관계 정의
    saving_products = relationship("SavingProduct", back_populates="company")


class BankProduct(Base):
    __tablename__ = "bank_product"
    
    product_id = Column(String(255), primary_key=True)
    bank_id = Column(Integer, ForeignKey("bank.bank_id"))
    product_name = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    min_period_days = Column(Integer, nullable=True)
    max_period_days = Column(Integer, nullable=True)
    min_amount = Column(Integer, nullable=True)
    max_amount = Column(Integer, nullable=True)
    deposit_method = Column(Text, nullable=True)
    maturity = Column(Boolean, nullable=True)
    interest_payment_method = Column(Text, nullable=True)
    interest_type = Column(Text, nullable=True)
    base_interest_rate = Column(Float, nullable=True)
    protection = Column(Boolean, nullable=True)
    
    # 관계 정의
    bank = relationship("Bank", back_populates="products")
    benefits = relationship("BankProductBenefit", back_populates="product")
    channels = relationship("BankProductChannel", back_populates="product")


class BankProductBenefit(Base):
    __tablename__ = "bank_product_benefit"
    
    benefit_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(255), ForeignKey("bank_product.product_id"))
    benefit_condition = Column(Text, nullable=True)
    benefit_rate = Column(Float, nullable=True)
    
    # 관계 정의
    product = relationship("BankProduct", back_populates="benefits")


class BankProductChannel(Base):
    __tablename__ = "bank_product_channel"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(255), ForeignKey("bank_product.product_id"))
    channel_code = Column(String(255), ForeignKey("channel_master.channel_code"))
    channel_type = Column(Text, nullable=True)
    
    # 관계 정의
    product = relationship("BankProduct", back_populates="channels")
    channel = relationship("ChannelMaster", back_populates="product_channels")


class ChannelMaster(Base):
    __tablename__ = "channel_master"
    
    channel_code = Column(String(255), primary_key=True)
    channel_name = Column(Text, nullable=True)
    
    # 관계 정의
    product_channels = relationship("BankProductChannel", back_populates="channel")


class FundCompany(Base):
    __tablename__ = "fund_company"
    
    company_id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), unique=True)
    
    # 관계 정의
    funds = relationship("Fund", back_populates="company")


class FundType(Base):
    __tablename__ = "fund_type"
    
    type_id = Column(Integer, primary_key=True, autoincrement=True)
    large_category = Column(String(255), nullable=True)
    mid_category = Column(String(255), nullable=True)
    small_category = Column(String(255), nullable=True)
    
    # 관계 정의
    funds = relationship("Fund", back_populates="fund_type")


class Fund(Base):
    __tablename__ = "fund"
    
    fund_id = Column(String(255), primary_key=True)
    fund_name = Column(Text, nullable=True)
    company_id = Column(Integer, ForeignKey("fund_company.company_id"))
    type_id = Column(Integer, ForeignKey("fund_type.type_id"))
    setup_date = Column(Date, nullable=True)
    
    # 관계 정의
    company = relationship("FundCompany", back_populates="funds")
    fund_type = relationship("FundType", back_populates="funds")
    performances = relationship("FundPerformance", back_populates="fund")


class FundPerformance(Base):
    __tablename__ = "fund_performance"
    
    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_id = Column(String(255), ForeignKey("fund.fund_id"))
    return_1m = Column(Float, nullable=True)
    return_3m = Column(Float, nullable=True)
    return_6m = Column(Float, nullable=True)
    return_1y = Column(Float, nullable=True)
    stddev_1y = Column(Float, nullable=True)
    sharpe_ratio_1y = Column(Float, nullable=True)
    
    # 관계 정의
    fund = relationship("Fund", back_populates="performances")


class SavingProduct(Base):
    __tablename__ = "saving_product"
    
    fin_prdt_cd = Column(String(40), primary_key=True)
    dcls_month = Column(String(6), nullable=True)
    fin_co_no = Column(String(20), ForeignKey("bank_company.fin_co_no"))
    fin_prdt_nm = Column(String(255), nullable=True)
    join_way = Column(Text, nullable=True)
    mtrt_int = Column(Text, nullable=True)
    spcl_cnd = Column(Text, nullable=True)
    join_deny = Column(Boolean, nullable=True)
    join_member = Column(Text, nullable=True)
    etc_note = Column(Text, nullable=True)
    max_limit = Column(DECIMAL(20, 4), nullable=True)
    dcls_strt_day = Column(String(10), nullable=True)
    dcls_end_day = Column(String(10), nullable=True)
    fin_co_subm_day = Column(String(14), nullable=True)
    
    # 관계 정의
    company = relationship("BankCompany", back_populates="saving_products")
    options = relationship("SavingProductOption", back_populates="product")


class SavingProductOption(Base):
    __tablename__ = "saving_product_option"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fin_prdt_cd = Column(String(40), ForeignKey("saving_product.fin_prdt_cd"))
    intr_rate_type = Column(String(20), nullable=True)
    intr_rate_type_nm = Column(String(100), nullable=True)
    rsrv_type = Column(String(20), nullable=True)
    rsrv_type_nm = Column(String(100), nullable=True)
    save_trm = Column(Integer, nullable=True)
    intr_rate = Column(DECIMAL(5, 2), nullable=True)
    intr_rate2 = Column(DECIMAL(5, 2), nullable=True)
    
    # 관계 정의
    product = relationship("SavingProduct", back_populates="options")
