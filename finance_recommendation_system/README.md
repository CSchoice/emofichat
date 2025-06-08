# 금융 상품 추천 시스템

고객의 금융 데이터를 기반으로 개인화된 금융 상품을 추천하는 시스템입니다. 이 시스템은 고객 대화나 감정 데이터 없이 순수하게 금융 데이터만을 활용하여 추천을 제공합니다.

## 주요 기능

- **데이터 처리**: 다양한 금융 데이터 소스를 로드하고 전처리합니다.
- **특성 공학**: 금융 건강 점수, 행동 패턴, 고객 세그먼트 등의 고급 특성을 생성합니다.
- **모델 학습**: LightGBM, XGBoost, 랜덤 포레스트 등 다양한 머신러닝 알고리즘을 사용하여 추천 모델을 학습합니다.
- **추천 엔진**: 학습된 모델을 사용하여 고객에게 맞춤형 금융 상품을 추천합니다.
- **API 서비스**: FastAPI를 사용하여 추천 기능을 API로 제공합니다.

## 시스템 구조

```
finance_recommendation_system/
├── src/
│   ├── data_processing/
│   │   ├── data_loader.py       # 금융 데이터 로드
│   │   └── data_preprocessor.py # 데이터 전처리
│   ├── feature_engineering/
│   │   └── feature_generator.py # 특성 생성
│   ├── model_training/
│   │   └── model_trainer.py     # 모델 학습
│   ├── recommendation_engine/
│   │   └── recommender.py       # 추천 엔진
│   ├── api/
│   │   └── recommendation_api.py # API 엔드포인트
│   └── main.py                  # 메인 애플리케이션
├── data/                        # 데이터 디렉토리
├── models/                      # 모델 저장 디렉토리
└── logs/                        # 로그 디렉토리
```

## 설치 방법

1. 필요한 패키지 설치:

```bash
pip install -r requirements.txt
```

2. 데이터 준비:
   - `data/` 디렉토리에 금융 데이터 파일을 위치시킵니다.
   - 금융 상품 데이터베이스를 `data/financial_products.csv`에 준비합니다.

## 사용 방법

### 모델 학습

```bash
python src/main.py --mode train --data_dir data --model_dir models
```

### 추천 테스트

```bash
python src/main.py --mode recommend --data_dir data --model_dir models
```

### API 서버 실행

```bash
python src/main.py --mode api
```

또는 직접 FastAPI 서버 실행:

```bash
uvicorn src.api.recommendation_api:app --host 0.0.0.0 --port 8000 --reload
```

## API 엔드포인트

- `GET /`: API 상태 확인
- `GET /health`: 건강 체크
- `GET /products`: 금융 상품 목록 조회
- `POST /recommend`: 고객에게 금융 상품 추천
- `POST /train`: 모델 학습

### 추천 요청 예시

```json
POST /recommend?product_type=deposit&model_type=lightgbm&top_n=3

{
  "customer_id": "CUST123456",
  "financial_data": {
    "age": 35,
    "bal_B0M": 5000000,
    "amt_credit_limit_use": 1000000,
    "bal_ca_B0M": 200000,
    "avg_growth_rate": 0.05,
    "vip_score": 7,
    "financial_health_score": 75
  }
}
```

## 의존성

- pandas: 데이터 처리
- numpy: 수치 연산
- scikit-learn: 전처리 및 모델링
- lightgbm, xgboost: 고급 모델링
- shap: 모델 해석
- fastapi, uvicorn: API 서비스
- joblib: 모델 저장 및 로드

## 라이센스

이 프로젝트는 MIT 라이센스를 따릅니다.
