"""
금융 상품 추천 시스템 메인 애플리케이션

데이터 로딩, 전처리, 특성 생성, 모델 학습 및 추천 엔진을 통합하여 실행합니다.
"""

import os
import sys
import logging
import pandas as pd
import argparse
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('finance_recommendation.log')
    ]
)
logger = logging.getLogger(__name__)

# 모듈 임포트
from data_processing.data_loader import FinancialDataLoader
from data_processing.data_preprocessor import FinancialDataPreprocessor
from feature_engineering.feature_generator import FinancialFeatureGenerator
from model_training.model_trainer import FinancialModelTrainer
from recommendation_engine.recommender import FinancialRecommender

def setup_directories():
    """필요한 디렉토리 생성"""
    directories = ['data', 'models', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"디렉토리 생성: {directory}")

def load_and_process_data(data_dir: str):
    """데이터 로드 및 전처리"""
    logger.info("데이터 로드 및 전처리 시작")
    
    # 데이터 로더 초기화
    data_loader = FinancialDataLoader(data_dir=data_dir)
    
    # 데이터 로드
    df = data_loader.load_data()
    logger.info(f"데이터 로드 완료: {df.shape[0]} 행, {df.shape[1]} 열")
    
    # 데이터 전처리
    preprocessor = FinancialDataPreprocessor()
    df = preprocessor.preprocess_data(df)
    logger.info(f"데이터 전처리 완료: {df.shape[0]} 행, {df.shape[1]} 열")
    
    return df

def generate_features(df: pd.DataFrame):
    """특성 생성"""
    logger.info("특성 생성 시작")
    
    # 특성 생성기 초기화
    feature_generator = FinancialFeatureGenerator()
    
    # 금융 건강 특성 생성
    df = feature_generator.generate_financial_health_features(df)
    
    # 행동 특성 생성
    df = feature_generator.generate_behavioral_features(df)
    
    # 고객 세그먼트 생성
    df = feature_generator.generate_customer_segments(df)
    
    # 특성 선택
    selected_features = feature_generator.select_features(df)
    
    logger.info(f"특성 생성 완료: {df.shape[0]} 행, {df.shape[1]} 열")
    logger.info(f"선택된 특성: {len(selected_features)} 개")
    
    return df, selected_features

def train_models(df: pd.DataFrame, selected_features: list, model_dir: str):
    """모델 학습"""
    logger.info("모델 학습 시작")
    
    # 모델 학습기 초기화
    model_trainer = FinancialModelTrainer(model_dir=model_dir)
    
    # 상품 유형별 모델 학습
    product_types = ['deposit', 'loan', 'fund']
    model_types = ['lightgbm', 'random_forest']
    
    for product_type in product_types:
        logger.info(f"{product_type} 상품 모델 학습 시작")
        
        # 타겟 변수 생성
        target = model_trainer.create_target_variable(df, product_type=product_type)
        
        # 특성 선택
        X = df[selected_features]
        y = target
        
        for model_type in model_types:
            logger.info(f"{product_type} {model_type} 모델 학습 시작")
            
            # 모델 학습
            model_info = model_trainer.train_model(
                X=X, 
                y=y, 
                model_type=model_type,
                product_type=product_type
            )
            
            # 모델 평가 지표 출력
            metrics = model_info['metrics']
            logger.info(f"{product_type} {model_type} 모델 성능:")
            for metric_name, metric_value in metrics.items():
                logger.info(f"  - {metric_name}: {metric_value:.4f}")
    
    logger.info("모델 학습 완료")

def test_recommendation(df: pd.DataFrame, model_dir: str, product_db_path: str):
    """추천 엔진 테스트"""
    logger.info("추천 엔진 테스트 시작")
    
    # 추천 엔진 초기화
    recommender = FinancialRecommender(model_dir=model_dir, product_db_path=product_db_path)
    
    # 테스트용 고객 데이터 선택 (첫 5명)
    test_customers = df.head(5)
    
    # 상품 유형별 추천 테스트
    product_types = ['deposit', 'loan', 'fund']
    model_type = 'lightgbm'  # 기본 모델 유형
    
    for product_type in product_types:
        logger.info(f"{product_type} 상품 추천 테스트")
        
        # 모델 로드
        if recommender.load_model(product_type, model_type):
            # 추천 수행
            recommendations = recommender.recommend_products(
                customer_data=test_customers,
                product_type=product_type,
                model_type=model_type,
                top_n=3
            )
            
            # 추천 결과 출력
            if recommendations:
                logger.info(f"{len(recommendations)} 개의 추천 결과 생성")
                for i, rec in enumerate(recommendations[:3]):  # 처음 3개만 출력
                    logger.info(f"추천 {i+1}:")
                    logger.info(f"  - 고객 ID: {rec['customer_id']}")
                    logger.info(f"  - 상품명: {rec['product_name']}")
                    logger.info(f"  - 점수: {rec['score']:.4f}")
                    logger.info(f"  - 이유: {rec['reasons'][0]}")
            else:
                logger.warning(f"{product_type} 상품 추천 결과가 없습니다.")
        else:
            logger.warning(f"{product_type} {model_type} 모델을 로드할 수 없습니다.")
    
    logger.info("추천 엔진 테스트 완료")

def run_api_server():
    """API 서버 실행"""
    logger.info("API 서버 실행")
    
    try:
        import uvicorn
        from api.recommendation_api import app
        
        # API 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except ImportError:
        logger.error("uvicorn 또는 FastAPI가 설치되어 있지 않습니다.")
        logger.info("설치 방법: pip install fastapi uvicorn")
    except Exception as e:
        logger.error(f"API 서버 실행 중 오류 발생: {str(e)}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="금융 상품 추천 시스템")
    parser.add_argument('--data_dir', type=str, default='data', help='데이터 디렉토리 경로')
    parser.add_argument('--model_dir', type=str, default='models', help='모델 저장 디렉토리 경로')
    parser.add_argument('--product_db', type=str, default='data/financial_products.csv', help='금융 상품 데이터베이스 경로')
    parser.add_argument('--mode', type=str, choices=['train', 'recommend', 'api'], default='train', help='실행 모드')
    
    args = parser.parse_args()
    
    try:
        # 디렉토리 설정
        setup_directories()
        
        if args.mode == 'train':
            # 데이터 로드 및 전처리
            df = load_and_process_data(args.data_dir)
            
            # 특성 생성
            df, selected_features = generate_features(df)
            
            # 모델 학습
            train_models(df, selected_features, args.model_dir)
            
            # 추천 엔진 테스트
            test_recommendation(df, args.model_dir, args.product_db)
            
            logger.info("모델 학습 및 테스트 완료")
            
        elif args.mode == 'recommend':
            # 데이터 로드 및 전처리
            df = load_and_process_data(args.data_dir)
            
            # 특성 생성
            df, selected_features = generate_features(df)
            
            # 추천 엔진 테스트
            test_recommendation(df, args.model_dir, args.product_db)
            
            logger.info("추천 테스트 완료")
            
        elif args.mode == 'api':
            # API 서버 실행
            run_api_server()
            
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
