"""
데이터베이스 초기화 스크립트

MySQL 테이블을 생성하고 초기 데이터를 설정합니다.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateTable

from app.core.db import DB_URL
from app.models.database import (
    Base, User, EmotionRecord, Conversation, Message,
    FinancialProfile, RiskEvaluation, Product, Recommendation
)

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 샘플 금융 상품 데이터
SAMPLE_PRODUCTS = [
    # 예금 상품
    {
        "product_id": "DP001",
        "name": "안심 정기예금",
        "type": "deposit",
        "description": "안정적인 수익을 원하는 고객을 위한 정기예금 상품입니다.",
        "interest_rate": 3.5,
        "min_period": 12,
        "max_period": 36,
        "min_amount": 1000000,
        "risk_level": "low",
        "features": {
            "early_withdrawal": True,
            "auto_renewal": True,
            "interest_payment": "maturity"
        }
    },
    {
        "product_id": "DP002",
        "name": "더블 점프 적금",
        "type": "deposit",
        "description": "매월 일정액을 저축하여 목돈을 마련하는 적금 상품입니다.",
        "interest_rate": 4.2,
        "min_period": 6,
        "max_period": 24,
        "min_amount": 50000,
        "risk_level": "low",
        "features": {
            "early_withdrawal": False,
            "auto_renewal": False,
            "interest_payment": "monthly"
        }
    },
    {
        "product_id": "DP003",
        "name": "프리미엄 정기예금",
        "type": "deposit",
        "description": "고액 예치 고객을 위한 우대금리 정기예금 상품입니다.",
        "interest_rate": 3.8,
        "min_period": 12,
        "max_period": 60,
        "min_amount": 50000000,
        "risk_level": "low",
        "features": {
            "early_withdrawal": True,
            "auto_renewal": True,
            "interest_payment": "quarterly"
        }
    },
    # 펀드 상품
    {
        "product_id": "FD001",
        "name": "글로벌 주식 인덱스 펀드",
        "type": "fund",
        "description": "글로벌 주식 시장에 분산 투자하는 인덱스 펀드입니다.",
        "interest_rate": None,
        "min_period": None,
        "max_period": None,
        "min_amount": 100000,
        "risk_level": "medium",
        "features": {
            "fund_type": "equity",
            "management_fee": 0.5,
            "redemption_fee": 0.3,
            "regions": ["global"]
        }
    },
    {
        "product_id": "FD002",
        "name": "국내 채권형 펀드",
        "type": "fund",
        "description": "국내 우량 채권에 투자하여 안정적인 수익을 추구하는 펀드입니다.",
        "interest_rate": None,
        "min_period": None,
        "max_period": None,
        "min_amount": 500000,
        "risk_level": "low",
        "features": {
            "fund_type": "bond",
            "management_fee": 0.3,
            "redemption_fee": 0.2,
            "regions": ["domestic"]
        }
    },
    {
        "product_id": "FD003",
        "name": "테크 섹터 액티브 펀드",
        "type": "fund",
        "description": "글로벌 기술 기업에 집중 투자하는 액티브 운용 펀드입니다.",
        "interest_rate": None,
        "min_period": None,
        "max_period": None,
        "min_amount": 1000000,
        "risk_level": "high",
        "features": {
            "fund_type": "equity",
            "management_fee": 1.2,
            "redemption_fee": 0.5,
            "regions": ["global"],
            "sectors": ["technology"]
        }
    }
]


async def create_tables():
    """데이터베이스 테이블 생성"""
    engine = create_async_engine(DB_URL, echo=True)
    
    async with engine.begin() as conn:
        # 기존 테이블 삭제 (옵션)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("데이터베이스 테이블 생성 완료")
    return engine


async def insert_sample_products(engine):
    """샘플 금융 상품 데이터 추가"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    async with async_session() as session:
        # 기존 상품 데이터 확인
        from sqlalchemy.future import select
        result = await session.execute(select(Product))
        existing_products = result.scalars().all()
        
        if existing_products:
            logger.info(f"이미 {len(existing_products)}개의 상품이 등록되어 있습니다.")
            return
        
        # 샘플 상품 추가
        for product_data in SAMPLE_PRODUCTS:
            product = Product(**product_data)
            session.add(product)
        
        await session.commit()
    
    logger.info(f"{len(SAMPLE_PRODUCTS)}개의 샘플 금융 상품 데이터 추가 완료")


async def main():
    """데이터베이스 초기화 메인 함수"""
    try:
        # 테이블 생성
        engine = await create_tables()
        
        # 샘플 데이터 추가
        await insert_sample_products(engine)
        
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
