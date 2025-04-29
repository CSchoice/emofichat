from sqlalchemy import Column, String, BigInteger, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Bank(Base):
    __tablename__ = "bank"

    bank_id = Column(BigInteger, primary_key=True, autoincrement=True)
    bank_name = Column(String(255), unique=True)

class BankProduct(Base):
    __tablename__ = "bank_product"

    product_id = Column(String(255), primary_key=True)
    bank_id = Column(BigInteger, ForeignKey("bank.bank_id"))
    product_name = Column(Text)
    description = Column(Text)
    min_period_days = Column(BigInteger)
    max_period_days = Column(BigInteger)
    min_amount = Column(BigInteger)
    max_amount = Column(BigInteger)
    deposit_method = Column(Text)
    maturity = Column(BigInteger)
    interest_payment_method = Column(Text)
    interest_type = Column(Text)
    base_interest_rate = Column(Float)
    protection = Column(BigInteger)

class BankProductBenefit(Base):
    __tablename__ = "bank_product_benefit"

    benefit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(String(255), ForeignKey("bank_product.product_id"))
    benefit_condition = Column(Text)
    benefit_rate = Column(Float)

class BankProductChannel(Base):
    __tablename__ = "bank_product_channel"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(String(255), ForeignKey("bank_product.product_id"))
    channel_code = Column(String(255))
    channel_type = Column(Text)
