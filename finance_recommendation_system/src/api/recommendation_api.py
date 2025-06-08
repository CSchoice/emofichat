"""
금융 상품 추천 API 모듈

FastAPI를 사용하여 금융 상품 추천 시스템의 API 엔드포인트를 제공합니다.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import logging
import os
import sys
import json
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 모듈 임포트
from data_processing.data_loader import FinancialDataLoader
from data_processing.data_preprocessor import FinancialDataPreprocessor
from feature_engineering.feature_generator import FinancialFeatureGenerator
from model_training.model_trainer import FinancialModelTrainer
from recommendation_engine.recommender import FinancialRecommender

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_logs.log')
    ]
)
logger = logging.getLogger(__name__)

# API 앱 생성
app = FastAPI(
    title="금융 상품 추천 API",
    description="금융 데이터를 기반으로 고객에게 맞춤형 금융 상품을 추천하는 API",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 환경에서는 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모델 및 데이터 경로 설정
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PRODUCT_DB_PATH = os.path.join(DATA_DIR, "financial_products.csv")

# 전역 객체
recommender = None

# 요청 모델
class CustomerDataRequest(BaseModel):
    customer_id: str = Field(..., description="고객 ID")
    financial_data: Dict[str, Any] = Field(..., description="고객 금융 데이터")

# 응답 모델
class ProductRecommendation(BaseModel):
    product_id: str = Field(..., description="상품 ID")
    product_name: str = Field(..., description="상품명")
    product_type: str = Field(..., description="상품 유형")
    score: float = Field(..., description="추천 점수")
    probability: float = Field(..., description="추천 확률")
    reasons: List[str] = Field(..., description="추천 이유")

class RecommendationResponse(BaseModel):
    customer_id: str = Field(..., description="고객 ID")
    recommendations: List[ProductRecommendation] = Field(..., description="추천 상품 목록")
    timestamp: str = Field(..., description="추천 시간")

# 추천 엔진 초기화 함수
def get_recommender():
    global recommender
    if recommender is None:
        try:
            # 상품 데이터베이스 확인
            if not os.path.exists(PRODUCT_DB_PATH):
                logger.warning(f"상품 데이터베이스 파일이 존재하지 않습니다: {PRODUCT_DB_PATH}")
                # 예시 상품 데이터 생성
                create_sample_product_data()
            
            # 추천 엔진 초기화
            recommender = FinancialRecommender(model_dir=MODEL_DIR, product_db_path=PRODUCT_DB_PATH)
            
            # 모델 로드 시도
            for product_type in ['deposit', 'loan', 'fund']:
                for model_type in ['lightgbm', 'random_forest']:
                    recommender.load_model(product_type, model_type)
            
            logger.info("추천 엔진 초기화 완료")
        except Exception as e:
            logger.error(f"추천 엔진 초기화 중 오류 발생: {str(e)}")
            raise HTTPException(status_code=500, detail=f"추천 엔진 초기화 실패: {str(e)}")
    
    return recommender

# 예시 상품 데이터 생성 함수
def create_sample_product_data():
    try:
        # 디렉토리 생성
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # 예금 상품 데이터
        deposit_products = [
            {
                "상품코드": "DP001",
                "상품명": "프리미엄 정기예금",
                "상품종류": "은행수신상품",
                "최고금리": 3.5,
                "계약기간개월수_최대구간": 24,
                "가입금액_최소구간": 1000000,
                "상품설명": "고금리 정기예금 상품으로 목돈 마련에 적합합니다."
            },
            {
                "상품코드": "DP002",
                "상품명": "VIP 자유적금",
                "상품종류": "은행수신상품",
                "최고금리": 3.2,
                "계약기간개월수_최대구간": 36,
                "가입금액_최소구간": 100000,
                "상품설명": "매월 자유롭게 납입하는 적금 상품입니다."
            },
            {
                "상품코드": "DP003",
                "상품명": "디지털 입출금통장",
                "상품종류": "은행수신상품",
                "최고금리": 1.0,
                "계약기간개월수_최대구간": 0,
                "가입금액_최소구간": 0,
                "상품설명": "수수료 면제 혜택이 있는 입출금 통장입니다."
            },
            {
                "상품코드": "DP004",
                "상품명": "청년 희망 적금",
                "상품종류": "은행수신상품",
                "최고금리": 4.0,
                "계약기간개월수_최대구간": 24,
                "가입금액_최소구간": 50000,
                "상품설명": "청년층을 위한 고금리 적금 상품입니다."
            },
            {
                "상품코드": "DP005",
                "상품명": "골드 정기예금",
                "상품종류": "은행수신상품",
                "최고금리": 3.8,
                "계약기간개월수_최대구간": 12,
                "가입금액_최소구간": 5000000,
                "상품설명": "단기 고금리 정기예금 상품입니다."
            }
        ]
        
        # 대출 상품 데이터
        loan_products = [
            {
                "상품코드": "LN001",
                "상품명": "신용대출 플러스",
                "상품종류": "은행여신상품",
                "기본금리": 4.5,
                "대출기간": "5년",
                "최대한도": 100000000,
                "상품설명": "우량 고객을 위한 저금리 신용대출 상품입니다."
            },
            {
                "상품코드": "LN002",
                "상품명": "주택담보대출",
                "상품종류": "은행여신상품",
                "기본금리": 3.8,
                "대출기간": "30년",
                "최대한도": 500000000,
                "상품설명": "주택 구입 및 보수를 위한 담보대출 상품입니다."
            },
            {
                "상품코드": "LN003",
                "상품명": "비상금 대출",
                "상품종류": "은행여신상품",
                "기본금리": 6.5,
                "대출기간": "1년",
                "최대한도": 10000000,
                "상품설명": "급전이 필요할 때 이용하는 단기 대출 상품입니다."
            },
            {
                "상품코드": "LN004",
                "상품명": "사업자 대출",
                "상품종류": "은행여신상품",
                "기본금리": 5.2,
                "대출기간": "7년",
                "최대한도": 300000000,
                "상품설명": "사업자를 위한 운영자금 대출 상품입니다."
            },
            {
                "상품코드": "LN005",
                "상품명": "카드 대환 대출",
                "상품종류": "은행여신상품",
                "기본금리": 7.0,
                "대출기간": "3년",
                "최대한도": 50000000,
                "상품설명": "고금리 카드 부채를 저금리로 전환하는 대출 상품입니다."
            }
        ]
        
        # 펀드 상품 데이터
        fund_products = [
            {
                "상품코드": "FD001",
                "상품명": "글로벌 주식형 펀드",
                "상품종류": "펀드상품",
                "펀드유형": "주식형",
                "위험등급": "2등급",
                "최소투자금액": 1000000,
                "상품설명": "글로벌 주식에 투자하는 고수익 추구형 펀드입니다."
            },
            {
                "상품코드": "FD002",
                "상품명": "국내 채권형 펀드",
                "상품종류": "펀드상품",
                "펀드유형": "채권형",
                "위험등급": "4등급",
                "최소투자금액": 500000,
                "상품설명": "국내 우량 채권에 투자하는 안정형 펀드입니다."
            },
            {
                "상품코드": "FD003",
                "상품명": "혼합형 자산배분 펀드",
                "상품종류": "펀드상품",
                "펀드유형": "혼합형",
                "위험등급": "3등급",
                "최소투자금액": 1000000,
                "상품설명": "주식과 채권에 균형있게 투자하는 중위험 펀드입니다."
            },
            {
                "상품코드": "FD004",
                "상품명": "테크놀로지 섹터 펀드",
                "상품종류": "펀드상품",
                "펀드유형": "주식형",
                "위험등급": "1등급",
                "최소투자금액": 2000000,
                "상품설명": "글로벌 기술주에 투자하는 고위험 고수익 펀드입니다."
            },
            {
                "상품코드": "FD005",
                "상품명": "단기 국공채 MMF",
                "상품종류": "펀드상품",
                "펀드유형": "MMF",
                "위험등급": "5등급",
                "최소투자금액": 100000,
                "상품설명": "단기 자금 운용에 적합한 초저위험 펀드입니다."
            }
        ]
        
        # 모든 상품 데이터 합치기
        all_products = deposit_products + loan_products + fund_products
        
        # CSV 파일로 저장
        df = pd.DataFrame(all_products)
        df.to_csv(PRODUCT_DB_PATH, index=False, encoding='utf-8')
        
        logger.info(f"예시 상품 데이터 생성 완료: {PRODUCT_DB_PATH}")
        
    except Exception as e:
        logger.error(f"예시 상품 데이터 생성 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"예시 상품 데이터 생성 실패: {str(e)}")

# 예시 모델 학습 함수
def train_sample_models():
    try:
        # 디렉토리 생성
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        # 예시 데이터 생성
        n_samples = 1000
        np.random.seed(42)
        
        # 특성 생성
        data = {
            'member_no': [f'CUST{i:06d}' for i in range(1, n_samples + 1)],
            'age': np.random.randint(20, 70, n_samples),
            'bal_B0M': np.random.lognormal(10, 2, n_samples) * 100000,  # 잔액
            'amt_credit_limit_use': np.random.lognormal(8, 2, n_samples) * 10000,  # 신용한도 사용액
            'bal_ca_B0M': np.random.lognormal(7, 2, n_samples) * 5000,  # 현금서비스 잔액
            'avg_growth_rate': np.random.normal(0.05, 0.1, n_samples),  # 평균 성장률
            'vip_score': np.random.randint(1, 10, n_samples),  # VIP 점수
            'financial_health_score': np.random.normal(60, 15, n_samples).clip(0, 100),  # 금융 건강 점수
            'credit_risk_score': np.random.beta(2, 5, n_samples),  # 신용 리스크 점수 (낮을수록 좋음)
            'cash_advance_preference': np.random.beta(2, 5, n_samples)  # 현금서비스 선호도
        }
        
        df = pd.DataFrame(data)
        
        # 특성 생성기
        feature_generator = FinancialFeatureGenerator()
        df = feature_generator.generate_financial_health_features(df)
        df = feature_generator.generate_behavioral_features(df)
        df = feature_generator.generate_customer_segments(df)
        
        # 모델 학습기
        model_trainer = FinancialModelTrainer(model_dir=MODEL_DIR)
        
        # 각 상품 유형별 모델 학습
        for product_type in ['deposit', 'loan', 'fund']:
            # 타겟 변수 생성
            target = model_trainer.create_target_variable(df, product_type=product_type)
            
            # 특성 선택
            X = df.drop(['member_no'], axis=1)
            y = target
            
            # 모델 학습
            for model_type in ['lightgbm', 'random_forest']:
                model_info = model_trainer.train_model(
                    X=X, 
                    y=y, 
                    model_type=model_type,
                    product_type=product_type
                )
                
                logger.info(f"{product_type} {model_type} 모델 학습 완료")
        
        logger.info("예시 모델 학습 완료")
        
    except Exception as e:
        logger.error(f"예시 모델 학습 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"예시 모델 학습 실패: {str(e)}")

# 시작 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    try:
        # 추천 엔진 초기화
        get_recommender()
    except Exception as e:
        logger.error(f"API 시작 중 오류 발생: {str(e)}")

# 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "금융 상품 추천 API에 오신 것을 환영합니다!"}

# 상품 추천 엔드포인트
@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_products(
    request: CustomerDataRequest,
    product_type: str = Query("deposit", description="추천할 상품 유형 (deposit, loan, fund)"),
    model_type: str = Query("lightgbm", description="사용할 모델 유형 (lightgbm, random_forest)"),
    top_n: int = Query(3, description="추천할 상품 수", ge=1, le=10),
    threshold: float = Query(0.5, description="추천 확률 임계값", ge=0.0, le=1.0),
    recommender: FinancialRecommender = Depends(get_recommender)
):
    try:
        # 고객 데이터 변환
        customer_data = pd.DataFrame([request.financial_data])
        
        # 필수 필드 확인
        if 'member_no' not in customer_data.columns:
            customer_data['member_no'] = request.customer_id
        
        # 모델 확인
        model_key = f"{product_type}_{model_type}"
        if model_key not in recommender.models:
            # 모델이 없는 경우 샘플 모델 학습
            logger.warning(f"모델이 없습니다: {model_key}. 샘플 모델을 학습합니다.")
            train_sample_models()
            recommender.load_model(product_type, model_type)
        
        # 상품 추천
        recommendations = recommender.recommend_products(
            customer_data=customer_data,
            product_type=product_type,
            model_type=model_type,
            top_n=top_n,
            threshold=threshold
        )
        
        # 응답 생성
        if not recommendations:
            # 추천 상품이 없는 경우
            return {
                "customer_id": request.customer_id,
                "recommendations": [],
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 응답 형식으로 변환
        product_recommendations = []
        for rec in recommendations:
            product_recommendations.append({
                "product_id": rec['product_id'],
                "product_name": rec['product_name'],
                "product_type": rec['product_type'],
                "score": rec['score'],
                "probability": rec['probability'],
                "reasons": rec['reasons']
            })
        
        return {
            "customer_id": request.customer_id,
            "recommendations": product_recommendations,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"상품 추천 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"상품 추천 실패: {str(e)}")

# 모델 학습 엔드포인트
@app.post("/train")
async def train_model(
    product_type: str = Query("deposit", description="학습할 모델의 상품 유형 (deposit, loan, fund)"),
    model_type: str = Query("lightgbm", description="학습할 모델 유형 (lightgbm, random_forest, xgboost)")
):
    try:
        # 샘플 모델 학습
        train_sample_models()
        
        # 추천 엔진 초기화 및 모델 로드
        recommender = get_recommender()
        recommender.load_model(product_type, model_type)
        
        return {
            "message": f"{product_type} {model_type} 모델 학습 완료",
            "status": "success",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"모델 학습 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"모델 학습 실패: {str(e)}")

# 상품 목록 조회 엔드포인트
@app.get("/products")
async def get_products(
    product_type: str = Query(None, description="조회할 상품 유형 (deposit, loan, fund)"),
    recommender: FinancialRecommender = Depends(get_recommender)
):
    try:
        # 상품 데이터베이스 확인
        if not recommender.products:
            return {
                "message": "상품 데이터가 없습니다.",
                "products": []
            }
        
        # 상품 유형별 필터링
        if product_type and product_type in recommender.products:
            products = recommender.products[product_type].to_dict(orient='records')
        else:
            # 모든 상품 반환
            products = []
            for p_type, p_df in recommender.products.items():
                products.extend(p_df.to_dict(orient='records'))
        
        return {
            "message": "상품 목록 조회 성공",
            "product_count": len(products),
            "products": products
        }
        
    except Exception as e:
        logger.error(f"상품 목록 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"상품 목록 조회 실패: {str(e)}")

# 건강 체크 엔드포인트
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# 메인 실행 코드
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
