"""
감정 분류기

사용자 메시지의 감정을 분류하고 금융 관련 여부를 판단합니다.
"""

import re
import logging
from typing import Dict, Any

from app.services.emotion.analyzer import get_emotion_analyzer

# 로거 설정
logger = logging.getLogger(__name__)

# 금융 관련 단어 목록
FINANCE_KEYWORDS = [
    # 금융 상품
    "대출", "적금", "예금", "저축", "계좌", "카드", "신용카드", "체크카드", 
    "이자", "이자율", "대금", "한도", "한도액", "월급", "연봉", "소득",
    "지출", "돈", "금액", "수입", "지불", "갚", "빚", "부채", "연체",
    # 금융 상태 
    "재정", "자산", "부채", "돈 문제", "금융", "경제", "투자", "주식", "펀드", 
    "저축", "연금", "보험", "세금", "납부", "공과금",
    # 감정 상태 + 금융
    "돈 걱정", "돈 불안", "돈 스트레스", "금융 스트레스", "빚 걱정",
    "대출 걱정", "카드값", "카드대금", "연체", "연체료", "연체 이자",
    # 생활비 관련
    "생활비", "주거비", "식비", "교통비", "의료비", "교육비", "통신비",
    "공과금", "관리비", "보험료", "렌트비", "월세", "전세"
]

# 금융 관련 정규식 패턴
FINANCE_PATTERNS = [
    r'\d+만원', r'\d+천원', r'\d+억원',  # 금액 패턴
    r'\d+%', r'\d+ ?퍼센트',            # 퍼센트 패턴
    r'연 ?\d+(?:\.\d+)?%'              # 이자율 패턴
]

class EmotionClassifier:
    """감정 분류 및 주제 탐지 클래스"""
    
    def __init__(self):
        self.emotion_analyzer = get_emotion_analyzer()
        
    def is_finance_topic(self, message: str) -> bool:
        """
        사용자 메시지가 금융 관련인지 판단
        
        Args:
            message: 사용자 메시지
            
        Returns:
            금융 관련 여부 (True/False)
        """
        # 텍스트 전처리
        text = message.lower()
        
        # 1. 금융 키워드 확인
        for keyword in FINANCE_KEYWORDS:
            if keyword in text:
                return True
        
        # 2. 금융 패턴 확인 
        for pattern in FINANCE_PATTERNS:
            if re.search(pattern, text):
                return True
                
        return False
        
    def analyze_emotion(self, message: str) -> Dict[str, Any]:
        """
        사용자 메시지의 감정을 분석
        
        Args:
            message: 사용자 메시지
            
        Returns:
            감정 분석 결과가 담긴 딕셔너리
        """
        try:
            # 감정 분석 수행
            emotion_result = self.emotion_analyzer.analyze(message)
            return emotion_result
        except Exception as e:
            logger.error(f"감정 분석 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본값 반환
            return {
                "dominant_emotion": "중립",
                "dominant_score": 1.0,
                "is_negative": False,
                "is_anxious": False,
                "all_emotions": {
                    "화남": 0.0, "혐오": 0.0, "공포": 0.0, "행복": 0.0,
                    "중립": 1.0, "슬픔": 0.0, "걱정": 0.0, "놀람": 0.0
                }
            }
            
    def analyze_message(self, message: str) -> Dict[str, Any]:
        """
        사용자 메시지를 종합적으로 분석
        
        Args:
            message: 사용자 메시지
            
        Returns:
            메시지 분석 결과가 담긴 딕셔너리
            {
                "is_finance": True,
                "emotion": {
                    "dominant_emotion": "걱정",
                    "dominant_score": 0.75,
                    "is_negative": True,
                    "is_anxious": True,
                    "all_emotions": {...}
                }
            }
        """
        # 금융 관련 여부 판단
        is_finance = self.is_finance_topic(message)
        
        # 감정 분석
        emotion_data = self.analyze_emotion(message)
        
        # 결과 구성
        return {
            "is_finance": is_finance,
            "emotion": emotion_data
        }

# 싱글톤 인스턴스
_emotion_classifier = None

def get_emotion_classifier() -> EmotionClassifier:
    """감정 분류기 싱글톤 인스턴스 반환"""
    global _emotion_classifier
    if _emotion_classifier is None:
        _emotion_classifier = EmotionClassifier()
    return _emotion_classifier

# 기존 코드와의 호환성을 위한 함수들
def is_finance_topic(message: str) -> bool:
    """
    사용자 메시지가 금융 관련인지 판단 (호환성 함수)
    """
    classifier = get_emotion_classifier()
    return classifier.is_finance_topic(message)
    
def analyze_emotion(message: str) -> Dict[str, Any]:
    """
    사용자 메시지의 감정을 분석 (호환성 함수)
    """
    classifier = get_emotion_classifier()
    return classifier.analyze_emotion(message)
    
def analyze_message(message: str) -> Dict[str, Any]:
    """
    사용자 메시지를 종합적으로 분석 (호환성 함수)
    """
    classifier = get_emotion_classifier()
    return classifier.analyze_message(message)
