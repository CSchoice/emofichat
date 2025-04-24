import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DB_URL = os.getenv(
    "DB_URL",
    "mysql+aiomysql://emofinance:emofinance@mysql_emofinance:3306/emofinance"
)
engine = create_async_engine(DB_URL, echo=False, pool_recycle=3600)
SessionMaker = async_sessionmaker(engine, expire_on_commit=False)