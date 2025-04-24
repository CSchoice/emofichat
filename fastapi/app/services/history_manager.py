from __future__ import annotations

import logging
from typing import Optional, List, Tuple

from app.services.generic_chat import load_history, save_history

# 로거 설정
logger = logging.getLogger(__name__)

async def get_compact_history(user_id: str, max_history: int = 2) -> str:
    """사용자의 최근 대화 히스토리를 요약해서 가져오는 함수
    
    토큰 절약을 위해 최대 max_history개의 대화만 가져오고, 요약한 형태로 반환합니다.
    """
    try:
        # 기존 load_history 함수 활용
        history = await load_history(user_id)
        
        if not history or len(history) == 0:
            return ""
        
        # 최신 대화 max_history개만 가져오기 (현재 대화 제외)
        recent_history = history[-max_history:] if len(history) > max_history else history
        
        # 요약형 형태로 간결한 히스토리 구성
        compact_history = ""
        for idx, (user_q, bot_a) in enumerate(recent_history):
            keywords = extract_keywords(user_q)
            summary = summarize_response(bot_a)
            compact_history += f"\n최근 대화 {idx+1}: 질문 [{keywords}] / 답변 [{summary}]"
        
        return compact_history
    except Exception as e:
        logger.warning(f"사용자 {user_id} 히스토리 요약 오류: {str(e)}")
        return ""

def extract_keywords(text: str, max_words: int = 5) -> str:
    """사용자 질문에서 주요 키워드만 추출
    
    토큰 절약을 위해 질문을 간략하게 요약합니다.
    """
    # 짧은 질문은 그대로 반환
    if len(text.split()) <= max_words:
        return text
    
    # 재무 관련 키워드 정의
    finance_keywords = [
        "가계", "소득", "지출", "저축", "투자", "비용", "자산", "대출", "신용", "카드", "이자", "금액", 
        "재테크", "연체", "재무", "은행", "상환", "보험", "연금", "주식", "카드", "기획", "경제", 
        "보유", "자금", "가능", "공과", "적금", "재산"
    ]
    
    words = text.split()
    important_words = []
    
    # 재무 키워드 우선 추출
    for word in words:
        for keyword in finance_keywords:
            if keyword in word:
                important_words.append(word)
                break
        if len(important_words) >= max_words:
            break
    
    # 충분한 키워드가 없으면 질문에서 중요 단어 추가
    if len(important_words) < max_words:
        for word in words:
            if word not in important_words and ("?" in word or "요" in word):
                important_words.append(word)
            if len(important_words) >= max_words:
                break
    
    # 여전히 부족한 경우 나머지 단어 추가
    if len(important_words) < max_words:
        for word in words:
            if word not in important_words and len(word) > 1:  # 한 글자 이상인 단어만 추가
                important_words.append(word)
            if len(important_words) >= max_words:
                break
    
    return " ".join(important_words[:max_words])

def summarize_response(text: str, max_chars: int = 30) -> str:
    """챗봇 응답을 매우 간결하게 요약
    
    토큰 절약을 위해 응답을 간략하게 요약합니다.
    """
    if len(text) <= max_chars:
        return text
    
    # 접그마를 고려한 잘라내기
    if ". " in text[:max_chars]:
        return text[:max_chars].rsplit(". ", 1)[0] + "."
    else:
        return text[:max_chars] + "..."
