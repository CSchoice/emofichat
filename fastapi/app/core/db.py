import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import get_settings

# SQLAlchemy Base 클래스 생성
Base = declarative_base()


# 로컬 개발 환경용 DB URL
DB_URL = os.getenv(
    "DB_URL",
    "mysql+aiomysql://root:emo1234secure!@localhost:5431/emofinance"
)

# 디버그 출력
print(f"Connecting to database: {DB_URL}")

engine = create_async_engine(DB_URL, echo=False, pool_recycle=3600)
SessionMaker = async_sessionmaker(engine, expire_on_commit=False)