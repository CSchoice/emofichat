# app/core/config.py
import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv, find_dotenv   # pip install python-dotenv
from typing import Dict, Any, Optional

# ① .env 파일 찾기 (루트 위치)
BASE_DIR = Path(__file__).resolve().parents[2]
DOTENV_PATH = BASE_DIR / ".env"

# ② 환경변수 주입 (이미 있으면 override 안 함)
load_dotenv(dotenv_path=DOTENV_PATH, override=False)

# ③ 중앙화된 설정 관리 클래스
class Settings(BaseModel):
    """애플리케이션 설정 모델 (Pydantic)"""
    
    # 일반 설정
    APP_NAME: str = "Emotion-based Finance Chatbot"
    API_VERSION: str = "0.2.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # OpenAI 설정
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_ORG_ID: Optional[str] = Field(None, env="OPENAI_ORG_ID")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo-0125", env="OPENAI_MODEL")
    
    # 데이터베이스 설정
    DB_URL: str = Field(
        default="mysql+aiomysql://root:emo1234secure!@localhost:5431/emofinance", 
        env="DB_URL"
    )
    
    # Redis 설정
    REDIS_URL: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    
    # 로깅 설정
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # 성능 설정
    MAX_HISTORY_TURNS: int = Field(default=10, env="MAX_HISTORY_TURNS")
    
    class Config:
        env_file = ".env"

# ④ 전역 설정 인스턴스
_settings = None

def get_settings() -> Settings:
    """싱글톤 설정 객체 얻기"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# ⑤ 헬퍼 함수 (이전 버전 호환성)
def get_env(key: str, default: str | None = None) -> str:
    """환경변수 가져오기 (이전 코드 호환용)"""
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"[config] 필수 환경변수 {key} 가 없습니다")
    return value
