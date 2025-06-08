"""
감정 분석 엔진

사용자 메시지의 감정을 분석하여 금융 상담에 활용합니다.
model.safetensors, config.json, training_args.bin 파일을 사용합니다.
"""

import os
import logging
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, AutoConfig
from transformers import TextClassificationPipeline

# 로거 설정
logger = logging.getLogger(__name__)

# 모델 경로 설정
MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "emotion"
# 절대 경로로 변환
MODEL_DIR = MODEL_DIR.resolve()

class EmotionAnalyzer:
    """감정 분석 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.labels = ['슬픔', '중립', '화남', '걱정', '행복']
        self.is_loaded = False
        # 라벨 매핑 추가 (LABEL_X 형식의 라벨을 실제 감정으로 매핑)
        # 기본 라벨 매핑 제공 (모델에 따라 다를 수 있음)
        self.label_mapping = {
            'LABEL_0': '화남',     # angry
            'LABEL_1': '혐오',     # disgust/disqust
            'LABEL_2': '공포',     # fear
            'LABEL_3': '행복',     # happy
            'LABEL_4': '중립',     # neutral
            'LABEL_5': '슬픔',     # sad
            'LABEL_6': '놀람',     # surprise
            'LABEL_7': '화남;혐오',
            'LABEL_8': '화남;중립',
            'LABEL_9': '화남;중립;혐오',
            'LABEL_10': '화남;중립;혐오;공포;슬픔',
            'LABEL_11': '혐오',    # disqust 철자 변형
            'LABEL_12': '공포',
            'LABEL_13': '행복',
            'LABEL_14': '행복;화남;중립',
        }
        
    def load_model(self) -> bool:
        """감정 분석 모델 로드"""
        try:
            # 모델 디렉토리 확인
            if not MODEL_DIR.exists():
                logger.error(f"모델 디렉토리가 존재하지 않습니다: {MODEL_DIR}")
                return False
                
            # 모델 파일 확인
            model_files = list(MODEL_DIR.glob("*.safetensors")) + list(MODEL_DIR.glob("*.bin"))
            if not model_files:
                logger.error(f"모델 파일을 찾을 수 없습니다: {MODEL_DIR}")
                return False
                
            # 설정 파일 확인
            config_file = MODEL_DIR / "config.json"
            if not config_file.exists():
                logger.error(f"설정 파일을 찾을 수 없습니다: {config_file}")
                return False
                
            # 모델 로드
            logger.info(f"감정 분석 모델 로드 중: {MODEL_DIR}")
            
            # 설정 로드
            config = AutoConfig.from_pretrained(MODEL_DIR)
            
            # 라벨 매핑 업데이트
            if hasattr(config, 'id2label'):
                self.label_mapping = config.id2label
                logger.info(f"모델에서 라벨 매핑 로드: {self.label_mapping}")
            
            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
            
            # 모델 로드
            self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
            
            # 파이프라인 생성
            self.pipeline = TextClassificationPipeline(
                model=self.model, 
                tokenizer=self.tokenizer,
                return_all_scores=True
            )
            
            self.is_loaded = True
            logger.info("감정 분석 모델 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"감정 분석 모델 로드 실패: {str(e)}")
            return False
            
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        텍스트의 감정을 분석하여 결과 반환
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            감정 분석 결과가 담긴 딕셔너리
            {
                "dominant_emotion": "걱정",
                "dominant_score": 0.75,
                "is_negative": True,
                "is_anxious": True,
                "all_emotions": {
                    "화남": 0.1,
                    "혐오": 0.05,
                    "공포": 0.2,
                    "행복": 0.05,
                    "중립": 0.1,
                    "슬픔": 0.2,
                    "걱정": 0.75,
                    "놀람": 0.05
                }
            }
        """
        # 모델이 로드되지 않았으면 로드 시도
        if not self.is_loaded and not self.load_model():
            logger.error("감정 분석 모델이 로드되지 않았습니다.")
            return self._get_default_result()
            
        try:
            # 텍스트가 없으면 기본값 반환
            if not text or len(text.strip()) == 0:
                logger.warning("분석할 텍스트가 없습니다.")
                return self._get_default_result()
                
            # 텍스트 길이 제한 (토크나이저 최대 길이에 맞춤)
            max_length = self.tokenizer.model_max_length
            if max_length > 512:
                max_length = 512  # 안전한 최대 길이
                
            # 토큰화 및 길이 확인
            tokens = self.tokenizer.tokenize(text)
            if len(tokens) > max_length:
                logger.warning(f"텍스트가 너무 깁니다. {len(tokens)} 토큰 -> {max_length} 토큰으로 제한합니다.")
                text = self.tokenizer.convert_tokens_to_string(tokens[:max_length])
                
            # 감정 분석 수행
            result = self.pipeline(text)
            
            # 결과 처리
            return self._process_result(result[0])
            
        except Exception as e:
            logger.error(f"감정 분석 중 오류 발생: {str(e)}")
            return self._get_default_result()
            
    def _process_result(self, raw_result: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        모델의 원시 결과를 가공하여 반환
        
        Args:
            raw_result: 모델의 원시 결과
            
        Returns:
            가공된 감정 분석 결과
        """
        # 결과 정규화 및 매핑
        emotions = {}
        for item in raw_result:
            # 라벨 매핑
            label = item['label']
            if label in self.label_mapping:
                label = self.label_mapping[label]
                
            # 복합 감정 처리 (세미콜론으로 구분된 경우)
            if ';' in label:
                sub_labels = label.split(';')
                score = item['score'] / len(sub_labels)
                for sub_label in sub_labels:
                    emotions[sub_label] = emotions.get(sub_label, 0) + score
            else:
                emotions[label] = item['score']
                
        # 지원하는 감정 목록
        supported_emotions = ['화남', '혐오', '공포', '행복', '중립', '슬픔', '놀람', '걱정']
        
        # 걱정 감정 추가 처리 (공포 + 슬픔 조합으로 추정)
        if '걱정' not in emotions and '공포' in emotions and '슬픔' in emotions:
            emotions['걱정'] = (emotions['공포'] + emotions['슬픔']) / 2
            
        # 누락된 감정에 기본값 할당
        for emotion in supported_emotions:
            if emotion not in emotions:
                emotions[emotion] = 0.0
                
        # 주요 감정 및 점수 추출
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        
        # 부정적 감정 여부 판단
        negative_emotions = ['화남', '혐오', '공포', '슬픔', '걱정']
        is_negative = dominant_emotion[0] in negative_emotions
        
        # 불안 감정 여부 판단
        anxious_emotions = ['공포', '걱정']
        is_anxious = dominant_emotion[0] in anxious_emotions
        
        # 결과 구성
        return {
            "dominant_emotion": dominant_emotion[0],
            "dominant_score": dominant_emotion[1],
            "is_negative": is_negative,
            "is_anxious": is_anxious,
            "all_emotions": emotions
        }
        
    def _get_default_result(self) -> Dict[str, Any]:
        """기본 감정 분석 결과 반환"""
        return {
            "dominant_emotion": "중립",
            "dominant_score": 1.0,
            "is_negative": False,
            "is_anxious": False,
            "all_emotions": {
                "화남": 0.0,
                "혐오": 0.0,
                "공포": 0.0,
                "행복": 0.0,
                "중립": 1.0,
                "슬픔": 0.0,
                "걱정": 0.0,
                "놀람": 0.0
            }
        }

# 싱글톤 인스턴스
_emotion_analyzer = None

def get_emotion_analyzer() -> EmotionAnalyzer:
    """감정 분석기 싱글톤 인스턴스 반환"""
    global _emotion_analyzer
    if _emotion_analyzer is None:
        _emotion_analyzer = EmotionAnalyzer()
        _emotion_analyzer.load_model()
    return _emotion_analyzer
