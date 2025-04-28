"""
감정 분석 서비스

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
MODEL_DIR = Path(__file__).parent.parent / "models" / "emotion"
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
            'LABEL_15': '행복;공포',
            'LABEL_16': '행복;중립',
            'LABEL_17': '행복;중립;혐오',
            'LABEL_18': '행복;중립;공포',
            'LABEL_19': '행복;슬픔',
            'LABEL_20': '행복;놀람',
            'LABEL_21': '행복;놀람;중립',
            'LABEL_22': '중립',
            'LABEL_23': '중립;혐오',
            'LABEL_24': '중립;혐오;슬픔',
            'LABEL_25': '중립;공포',
            'LABEL_26': '중립;슬픔',
            'LABEL_27': '슬픔',
            'LABEL_28': '놀람',
            'LABEL_29': '놀람;중립'
        }
        
        # 추가 라벨 번호를 처리하기 위한 확장 매핑 (LABEL_X 형식의 모든 값에 대해 처리)
        # 이미 지정된 라벨 외의 추가 번호 처리
        max_defined_label = 29  # 위에서 정의한 최대 라벨 번호
        for i in range(max_defined_label + 1, 100):  # 최대 100까지 추가 라벨 예측처리
            self.label_mapping[f'LABEL_{i}'] = '중립'  # 기본값은 중립으로 설정
            
        # 로그에 정의되지 않은 라벨을 사용할 경우 추가 정보 로깅
        logger.info(f"감정 분석기 초기화: {len(self.label_mapping)} 개의 라벨 매핑 추가됨")
        
    def load_model(self):
        """감정 분석 모델 로드"""
        try:
            # 모델 디렉토리 존재 여부 확인
            if not os.path.exists(MODEL_DIR):
                logger.warning(f"모델 디렉토리가 존재하지 않습니다: {MODEL_DIR}")
                return False
            
            # 필요한 파일들 확인
            required_files = ["model.safetensors", "config.json", "training_args.bin"]
            for file in required_files:
                file_path = os.path.join(MODEL_DIR, file)
                if not os.path.exists(file_path):
                    logger.warning(f"필요한 모델 파일이 없습니다: {file_path}")
                    return False
            
            # 모델 설정 로드
            config = AutoConfig.from_pretrained(MODEL_DIR)
            
            # 모델 로드
            self.model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_DIR,
                config=config
            )
            
            # 토크나이저 로드 - KoBERT 또는 KoELECTRA 기반 모델 예상
            # 대형 사전학습 모델의 토크나이저 사용
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
            except:
                # 토크나이저가 없는 경우 기본 모델의 토크나이저 사용
                logger.info("모델 디렉토리에 토크나이저가 없어 기본 토크나이저를 사용합니다.")
                self.tokenizer = AutoTokenizer.from_pretrained("beomi/KcELECTRA-base-v2022")
            
            # 파이프라인 설정
            self.pipeline = TextClassificationPipeline(
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                top_k=None
            )
            
            self.is_loaded = True
            logger.info("감정 분석 모델 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"감정 분석 모델 로드 중 오류 발생: {str(e)}")
            return False
    
    def analyze(self, text: str) -> Dict[str, float]:
        """
        텍스트의 감정을 분석합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            감정별 확률 딕셔너리
            {
                "슬픔": 0.1,
                "중립": 0.2,
                "화남": 0.1,
                "걱정": 0.5,
                "행복": 0.1
            }
        """
        if not self.is_loaded:
            if not self.load_model():
                logger.warning("모델이 로드되지 않아 감정 분석을 수행할 수 없습니다.")
                return {"중립": 1.0}  # 기본값으로 중립 반환
        
        try:
            # 입력 텍스트가 너무 길면 잘라내기
            max_length = self.tokenizer.model_max_length
            if max_length and len(text) > max_length:
                text = text[:max_length]
            
            # 감정 분석 수행
            result = self.pipeline(text)
            
            # 결과를 딕셔너리로 변환
            if isinstance(result, list) and len(result) == 1:
                # 단일 결과
                scores = {}
                for label_score in result[0]:
                    # 라벨 변환 (LABEL_X 형식이면 매핑)
                    label = label_score['label']
                    
                    # 1. 모든 LABEL_X 형식 처리
                    if label.startswith("LABEL_"):
                        if label in self.label_mapping:
                            label = self.label_mapping[label]
                        else:
                            # 알 수 없는 LABEL_X는 중립으로 처리
                            logger.warning(f"알 수 없는 라벨 유형: {label}, 중립으로 처리합니다.")
                            label = "중립"
                    
                    score = label_score['score']
                    
                    # 이미 매핑한 동일 감정이 있는 경우 값 합치기 (예: 중립 + 중립)
                    if label in scores:
                        scores[label] += score
                    else:
                        scores[label] = score
                
                # 매핑된 라벨이 없는 경우 중립 추가
                if not scores:
                    scores["중립"] = 1.0
                    
                return scores
            else:
                # 여러 결과 또는 예상치 못한 형식
                logger.warning(f"예상치 못한 감정 분석 결과 형식: {result}")
                return {"중립": 1.0}
        
        except Exception as e:
            logger.error(f"감정 분석 중 오류 발생: {str(e)}")
            return {"중립": 1.0}  # 오류 시 중립 반환
    
    def get_dominant_emotion(self, text: str) -> Tuple[str, float]:
        """
        텍스트의 주요 감정을 분석합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            (감정 라벨, 확률) 튜플
        """
        emotions = self.analyze(text)
        
        # 확률이 가장 높은 감정 찾기
        dominant_emotion = max(emotions.items(), key=lambda x: x[1])
        return dominant_emotion
    
    def get_emotional_state(self, text: str) -> Dict[str, Any]:
        """
        텍스트의 감정 상태를 종합적으로 분석합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            감정 상태 정보가 담긴 딕셔너리
            {
                "dominant_emotion": "걱정",
                "dominant_score": 0.75,
                "is_negative": True,
                "is_anxious": True,
                "all_emotions": {"슬픔": 0.1, "중립": 0.1, ...}
            }
        """
        try:
            emotions = self.analyze(text)
            
            # LABEL_X 형식의 감정 라벨을 실제 감정 이름으로 정규화
            normalized_emotions = {}
            composite_emotions = {}
            
            for emotion, score in emotions.items():
                if emotion.startswith("LABEL_") and emotion in self.label_mapping:
                    mapped_emotion = self.label_mapping[emotion]
                    
                    # 복합 감정 처리 (세미콜론으로 구분된 감정)
                    if ";" in mapped_emotion:
                        composite_emotions[mapped_emotion] = score
                        # 복합 감정을 개별 감정으로 분할
                        parts = mapped_emotion.split(";")
                        weight = score / len(parts)  # 각 감정에 가중치 동일하게 분할
                        
                        for part in parts:
                            if part in normalized_emotions:
                                normalized_emotions[part] += weight
                            else:
                                normalized_emotions[part] = weight
                    else:
                        # 단일 감정 처리
                        if mapped_emotion in normalized_emotions:
                            normalized_emotions[mapped_emotion] += score
                        else:
                            normalized_emotions[mapped_emotion] = score
                else:
                    # 이미 매핑된 감정 처리
                    if emotion in normalized_emotions:
                        normalized_emotions[emotion] += score
                    else:
                        normalized_emotions[emotion] = score
            
            # 주요 감정 찾기
            if normalized_emotions:
                dominant_emotion, dominant_score = max(normalized_emotions.items(), key=lambda x: x[1])
            else:
                dominant_emotion, dominant_score = "중립", 1.0
            
            # 부정적 감정을 포함하는 카테고리 정의
            negative_emotions = ["화남", "혐오", "공포", "슬픔"]
            anxious_emotions = ["공포", "걱정"]
            
            # 부정적 감정 점수 계산
            negative_score = sum(normalized_emotions.get(emotion, 0) for emotion in negative_emotions)
            anxious_score = sum(normalized_emotions.get(emotion, 0) for emotion in anxious_emotions)
            
            # 복합 감정도 포함하여 결과 반환
            return {
                "dominant_emotion": dominant_emotion,
                "dominant_score": dominant_score,
                "is_negative": negative_score > 0.3,  # 더 낮은 임계값을 사용
                "is_anxious": anxious_score > 0.2,  # 더 낮은 임계값을 사용
                "all_emotions": normalized_emotions,
                "composite_emotions": composite_emotions  # 복합 감정 정보 추가
            }
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"감정 분석 중 오류: {str(e)}")
            # 오류 발생 시 기본값 반환
            return {
                "dominant_emotion": "중립",
                "dominant_score": 1.0,
                "is_negative": False,
                "is_anxious": False,
                "all_emotions": {"중립": 1.0},
                "composite_emotions": {}
            }

# 싱글톤 인스턴스
_emotion_analyzer = None

def get_emotion_analyzer():
    """감정 분석기 싱글톤 인스턴스 반환"""
    global _emotion_analyzer
    if _emotion_analyzer is None:
        _emotion_analyzer = EmotionAnalyzer()
        # 모델 미리 로드
        _emotion_analyzer.load_model()
    return _emotion_analyzer
