# 감정 기반 금융 챗봇 API

금융 메트릭 데이터와 감정 분석을 활용한 감정 기반 금융 상담 챗봇 API입니다.

## 기능 개요

- 일반 대화와 금융 상담 자동 분류
- 사용자 금융 데이터 기반 시나리오 판단
- **자체 학습된 감정 분석 모델을 통한 감정 상태 탐지**
- 감정 기반 맞춤형 금융 상담 제공
- Redis를 활용한 대화 이력 관리
- 멀티 스레드 및 비동기 요청 처리

## 시스템 구성

- FastAPI 웹 프레임워크
- MySQL 데이터베이스 (사용자 금융 데이터)
- Redis 캐시 (대화 이력 및 세션 관리)
- OpenAI GPT 모델 (자연어 처리)
- **Transformers 기반 감정 분석 모델 (슬픔, 중립, 화남, 걱정, 행복 분류)**

## 개발 환경 설정

### 필수 요구사항

- Python 3.9+
- Docker & Docker Compose
- OpenAI API 키
- PyTorch 및 Transformers 라이브러리

### 설치 및 실행

1. 가상 환경 설정

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. 환경 변수 설정 (.env 파일)

```
OPENAI_API_KEY=your_openai_api_key
ENVIRONMENT=development
DB_URL=mysql+aiomysql://emofinance:emofinance@localhost:3306/emofinance
REDIS_URL=redis://localhost:6379/0
```

3. 감정 분석 모델 설정

감정 분석 모델 파일(`model.safetensors`, `config.json`, `training_args.bin`)을 
`app/models/emotion` 디렉토리에 복사합니다.

모델 테스트:
```bash
python test_emotion_model.py
```

4. Docker로 의존성 서비스 실행

```bash
docker-compose up -d
```

5. 서버 실행

```bash
uvicorn main:app --reload
```

## API 엔드포인트

### 채팅 API

```
POST /api/chat

Request:
{
  "user_id": "사용자 고유 ID",
  "message": "사용자 메시지"
}

Response:
{
  "reply": "챗봇 응답 메시지",
  "scenario": {  # 금융 상담 시에만 포함
    "label": "시나리오 라벨",
    "probability": 0.85,
    "key_metrics": {
      "metric1": "값1",
      "metric2": "값2"
    }
  },
  "emotion": {  # 감정 분석 결과
    "dominant_emotion": "걱정",
    "dominant_score": 0.75,
    "is_negative": true,
    "is_anxious": true,
    "all_emotions": {
      "슬픔": 0.1,
      "중립": 0.1,
      "화남": 0.05,
      "걱정": 0.75,
      "행복": 0.0
    }
  }
}
```

## 감정 분석 모델

시스템은 5가지 감정을 분류하는 자체 학습된 모델을 사용합니다:

- **슬픔**: 금융 문제에 대한 좌절감, 실망감 표현
- **중립**: 감정 없는 일반적 문의나 정보 요청
- **화남**: 금융 문제에 대한 분노, 불만 표현
- **걱정**: 금융 미래에 대한 불안, 걱정 표현
- **행복**: 긍정적 금융 상황에 대한 만족감 표현

감정 분석 결과는 상담 스타일을 조정하는 데 사용됩니다:
- 슬픔/걱정: 공감형 접근을 우선하며 희망적 메시지 포함
- 화남: 객관적 정보 제공 후 실질적 해결책 제시
- 중립: 정보형 접근 우선
- 행복: 긍정적 피드백과 함께 미래 계획 논의

## 데이터베이스 구조

시스템은 다음과 같은 테이블 구조를 사용합니다:

1. `User` - 사용자 기본 정보
2. `CardUsage` - 카드 사용 현황
3. `Delinquency` - 연체 정보
4. `BalanceInfo` - 잔액 및 이자율 
5. `SpendingPattern` - 소비 패턴
6. `ScenarioLabel` - 감정 기반 시나리오 라벨링

## 프로젝트 구조

```
fastapi/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── chat.py       # API 엔드포인트
│   ├── core/
│   │   ├── config.py         # 설정 관리
│   │   ├── db.py             # 데이터베이스 연결
│   │   ├── dependencies.py   # 의존성 주입
│   │   ├── logger.py         # 로깅 설정
│   │   ├── openai_client.py  # OpenAI 클라이언트
│   │   └── redis_client.py   # Redis 클라이언트
│   ├── models/
│   │   ├── finance.py        # 데이터 모델
│   │   └── emotion/          # 감정 분석 모델 파일
│   ├── services/
│   │   ├── advice_templates.py  # 상담 템플릿
│   │   ├── emotion_analyzer.py  # 감정 분석 서비스
│   │   ├── finance_chat.py      # 금융 상담 서비스
│   │   ├── generic_chat.py      # 일반 채팅 서비스
│   │   ├── prompt_builder.py    # 프롬프트 생성
│   │   ├── scenario_engine.py   # 시나리오 판단 엔진
│   │   └── topic_detector.py    # 주제 감지 및 감정 분석
│   ├── util/
│   └── models.py             # Pydantic 모델
├── rules/
│   ├── scenario_rules.py     # 시나리오 규칙
│   └── thresholds.py         # 임계값 설정
├── scripts/
│   └── compute_thresholds.py # 임계값 계산
├── data/
├── logs/                     # 로그 파일
├── tests/                    # 테스트 코드
├── .env                      # 환경 변수
├── copy_model_files.py       # 모델 파일 복사 유틸리티
├── test_emotion_model.py     # 감정 분석 모델 테스트
├── docker-compose.yml        # Docker 설정
├── main.py                   # 애플리케이션 진입점
└── requirements.txt          # 의존성 패키지
```

## 다음 개발 계획

1. Redis 세션 저장소 구현
2. 테스트 코드 작성 (Pytest)
3. CI/CD 파이프라인 구축
4. 법규 준수 로깅 시스템 구현
5. Prometheus + Grafana 모니터링 설정
6. 감정 분석 모델 성능 개선 및 더 많은 감정 카테고리 추가

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 LICENSE 파일을 참조하세요.
