"""
금융 상품 추천 모델 학습 스크립트

금융 데이터를 로드하고 전처리한 후 상품 추천 모델을 학습하는 엔드투엔드 파이프라인
"""

import os
import sys
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('model_training.log')
    ]
)
logger = logging.getLogger(__name__)

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 모듈 임포트
from src.data_processing.data_loader import FinancialDataLoader
from src.data_processing.data_preprocessor import FinancialDataPreprocessor
from src.feature_engineering.feature_generator import FinancialFeatureGenerator
from src.model_training.model_trainer import FinancialModelTrainer

def setup_directories():
    """필요한 디렉토리 생성"""
    directories = ['data', 'models', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"디렉토리 생성: {directory}")

def load_and_preprocess_data(data_dir):
    """데이터 로드 및 전처리"""
    logger.info("데이터 로드 및 전처리 시작")
    
    # 데이터 로더 초기화
    data_loader = FinancialDataLoader(data_dir=data_dir)
    
    # 데이터 로드
    df = data_loader.load_data()
    logger.info(f"데이터 로드 완료: {df.shape[0]} 행, {df.shape[1]} 열")
    
    if df.empty:
        logger.error("데이터가 비어 있습니다.")
        return None
    
    # 데이터 전처리
    preprocessor = FinancialDataPreprocessor()
    df = preprocessor.preprocess_data(df)
    logger.info(f"데이터 전처리 완료: {df.shape[0]} 행, {df.shape[1]} 열")
    
    return df

def generate_features(df):
    """특성 생성"""
    logger.info("특성 생성 시작")
    
    if df is None or df.empty:
        logger.error("특성 생성을 위한 데이터가 없습니다.")
        return None, []
    
    # 특성 생성기 초기화
    feature_generator = FinancialFeatureGenerator()
    
    # 금융 건강 특성 생성
    df = feature_generator.generate_financial_health_features(df)
    logger.info("금융 건강 특성 생성 완료")
    
    # 행동 특성 생성
    df = feature_generator.generate_behavioral_features(df)
    logger.info("행동 특성 생성 완료")
    
    # 고객 세그먼트 생성
    df = feature_generator.generate_customer_segments(df)
    logger.info("고객 세그먼트 생성 완료")
    
    # 중요 특성 선택
    selected_features = feature_generator.select_features(df)
    logger.info(f"특성 선택 완료: {len(selected_features)} 개 특성 선택됨")
    
    return df, selected_features

def create_target_variables(df, model_trainer):
    """타겟 변수 생성"""
    logger.info("타겟 변수 생성 시작")
    
    if df is None or df.empty:
        logger.error("타겟 변수 생성을 위한 데이터가 없습니다.")
        return {}
    
    targets = {}
    
    # 예금 상품 타겟 변수
    deposit_target = model_trainer.create_target_variable(df, product_type='deposit')
    targets['deposit'] = deposit_target
    logger.info(f"예금 상품 타겟 변수 생성 완료: 양성 비율 {deposit_target.mean():.2f}")
    
    # 대출 상품 타겟 변수
    loan_target = model_trainer.create_target_variable(df, product_type='loan')
    targets['loan'] = loan_target
    logger.info(f"대출 상품 타겟 변수 생성 완료: 양성 비율 {loan_target.mean():.2f}")
    
    # 펀드 상품 타겟 변수
    fund_target = model_trainer.create_target_variable(df, product_type='fund')
    targets['fund'] = fund_target
    logger.info(f"펀드 상품 타겟 변수 생성 완료: 양성 비율 {fund_target.mean():.2f}")
    
    return targets

def train_models(df, selected_features, targets, model_dir):
    """모델 학습"""
    logger.info("모델 학습 시작")
    
    if df is None or df.empty or not targets:
        logger.error("모델 학습을 위한 데이터가 없습니다.")
        return {}
    
    # 모델 학습기 초기화
    model_trainer = FinancialModelTrainer(model_dir=model_dir)
    
    # 학습 결과 저장
    results = {}
    
    # 모델 유형
    model_types = ['lightgbm', 'random_forest', 'xgboost']
    
    # 각 상품 유형별 모델 학습
    for product_type, target in targets.items():
        logger.info(f"{product_type} 상품 모델 학습 시작")
        
        # 특성 데이터 준비
        X = df[selected_features].copy()
        y = target
        
        product_results = {}
        
        # 각 모델 유형별 학습
        for model_type in model_types:
            logger.info(f"{product_type} {model_type} 모델 학습 시작")
            
            try:
                # 기본 모델 학습
                model_info = model_trainer.train_model(
                    X=X,
                    y=y,
                    model_type=model_type,
                    product_type=product_type
                )
                
                # 하이퍼파라미터 튜닝 (선택적)
                if model_type == 'lightgbm':  # 대표 모델만 튜닝
                    logger.info(f"{product_type} {model_type} 하이퍼파라미터 튜닝 시작")
                    tuning_result = model_trainer.tune_hyperparameters(
                        X=X,
                        y=y,
                        model_type=model_type,
                        cv=5,
                        n_iter=20
                    )
                    
                    # 튜닝된 파라미터로 모델 재학습
                    model_info = model_trainer.train_model(
                        X=X,
                        y=y,
                        model_type=model_type,
                        product_type=product_type,
                        hyperparams=tuning_result['best_params']
                    )
                    
                    logger.info(f"{product_type} {model_type} 튜닝 완료: {tuning_result['best_score']:.4f}")
                
                # 모델 성능 출력
                metrics = model_info['metrics']
                logger.info(f"{product_type} {model_type} 모델 성능:")
                for metric_name, metric_value in metrics.items():
                    logger.info(f"  - {metric_name}: {metric_value:.4f}")
                
                # 특성 중요도 출력
                importances = model_info['feature_importances']
                top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10]
                logger.info(f"{product_type} {model_type} 주요 특성:")
                for feature, importance in top_features:
                    logger.info(f"  - {feature}: {importance:.4f}")
                
                # 결과 저장
                product_results[model_type] = {
                    'metrics': metrics,
                    'top_features': top_features
                }
                
            except Exception as e:
                logger.error(f"{product_type} {model_type} 모델 학습 중 오류 발생: {str(e)}")
        
        results[product_type] = product_results
    
    return results

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="금융 상품 추천 모델 학습")
    parser.add_argument('--data_dir', type=str, default='data', help='데이터 디렉토리 경로')
    parser.add_argument('--model_dir', type=str, default='models', help='모델 저장 디렉토리 경로')
    
    args = parser.parse_args()
    
    # 시작 시간 기록
    start_time = datetime.now()
    logger.info(f"금융 상품 추천 모델 학습 시작: {start_time}")
    
    try:
        # 디렉토리 설정
        setup_directories()
        
        # 데이터 로드 및 전처리
        df = load_and_preprocess_data(args.data_dir)
        
        if df is not None and not df.empty:
            # 특성 생성
            df, selected_features = generate_features(df)
            
            if df is not None and not df.empty:
                # 모델 학습기 초기화 (타겟 변수 생성용)
                model_trainer = FinancialModelTrainer(model_dir=args.model_dir)
                
                # 타겟 변수 생성
                targets = create_target_variables(df, model_trainer)
                
                if targets:
                    # 모델 학습
                    results = train_models(df, selected_features, targets, args.model_dir)
                    
                    # 결과 요약
                    logger.info("모델 학습 결과 요약:")
                    for product_type, product_results in results.items():
                        logger.info(f"{product_type} 상품:")
                        for model_type, model_result in product_results.items():
                            metrics = model_result['metrics']
                            logger.info(f"  - {model_type}: AUC={metrics.get('auc', 0):.4f}, F1={metrics.get('f1', 0):.4f}")
    
    except Exception as e:
        logger.error(f"모델 학습 중 오류 발생: {str(e)}")
    
    # 종료 시간 기록
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    logger.info(f"금융 상품 추천 모델 학습 완료: {end_time} (소요 시간: {elapsed_time})")

if __name__ == "__main__":
    main()
