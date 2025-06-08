from sqlalchemy import Column, BigInteger, String, Float, Date, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FundCompany(Base):
    __tablename__ = "fund_company"

    company_id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_name = Column(String(255), unique=True)

class FundType(Base):
    __tablename__ = "fund_type"

    type_id = Column(BigInteger, primary_key=True, autoincrement=True)
    large_category = Column(String(255))
    mid_category = Column(String(255))
    small_category = Column(String(255))

class Fund(Base):
    __tablename__ = "fund"

    fund_id = Column(String(255), primary_key=True)
    fund_name = Column(String(255))
    company_id = Column(BigInteger)
    type_id = Column(BigInteger)
    setup_date = Column(Date)

class FundPerformance(Base):
    __tablename__ = "fund_performance"

    performance_id = Column(BigInteger, primary_key=True, autoincrement=True)
    fund_id = Column(String(255))
    return_1m = Column(Float)
    return_3m = Column(Float)
    return_6m = Column(Float)
    return_1y = Column(Float)
    stddev_1y = Column(Float)
    sharpe_ratio_1y = Column(Float)
