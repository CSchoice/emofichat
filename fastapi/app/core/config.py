# app/core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv   # pip install python-dotenv

# ① .env 파일 찾기 (루트 위치)
DOTENV = find_dotenv() or Path(__file__).resolve().parents[2] / ".env"

# ② 환경변수 주입 (이미 있으면 override 안 함)
load_dotenv(DOTENV, override=False)

# ③ 헬퍼 함수 (선택)
def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"[config] 필수 환경변수 {key} 가 없습니다")
    return value
