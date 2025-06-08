"""
금융 추천 모델 학습 모듈

다양한 머신러닝 알고리즘을 사용하여 금융 상품 추천 모델을 학습하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
import os
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
import lightgbm as lgb
import shap

logger = logging.getLogger(__name__)

class FinancialModelTrainer:
    """금융 추천 모델 학습 클래스"""
    
    def __init__(self, model_dir: str = "models"):
        """
        금융 추천 모델 학습기 초기화
        
        Args:
            model_dir: 모델 저장 디렉토리
        """
        self.model_dir = model_dir
        self.models = {}
        self.feature_importances = {}
        self.model_metrics = {}
        self.shap_values = {}
        
        # 모델 저장 디렉토리 생성
        os.makedirs(self.model_dir, exist_ok=True)
    
    def train_model(
        self, 
        X: pd.DataFrame, 
        y: pd.Series, 
        model_type: str = 'lightgbm',
        product_type: str = 'deposit',
        test_size: float = 0.2,
        random_state: int = 42,
        hyperparams: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        모델 학습
        
        Args:
            X: 특성 데이터프레임
            y: 타겟 변수
            model_type: 모델 유형 ('lightgbm', 'xgboost', 'random_forest', 'gradient_boosting', 'logistic_regression')
            product_type: 상품 유형 ('deposit', 'fund', 'loan')
            test_size: 테스트 데이터 비율
            random_state: 랜덤 시드
            hyperparams: 하이퍼파라미터 (None인 경우 기본값 사용)
            
        Returns:
            Dict[str, Any]: 학습 결과 정보
        """
        # 학습/테스트 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # 모델 선택 및 학습
        model = self._get_model(model_type, hyperparams)
        model.fit(X_train, y_train)
        
        # 예측 및 평가
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
        
        # 평가 지표 계산
        metrics = self._calculate_metrics(y_test, y_pred, y_prob)
        
        # 특성 중요도 계산
        feature_importances = self._calculate_feature_importance(model, X.columns)
        
        # SHAP 값 계산
        shap_values = self._calculate_shap_values(model, X_test)
        
        # 모델 및 관련 정보 저장
        model_info = {
            'model': model,
            'model_type': model_type,
            'product_type': product_type,
            'feature_names': X.columns.tolist(),
            'metrics': metrics,
            'feature_importances': feature_importances,
            'shap_values': shap_values,
            'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 모델 저장
        model_key = f"{product_type}_{model_type}"
        self.models[model_key] = model_info
        
        # 모델 파일로 저장
        self._save_model(model_key, model_info)
        
        return model_info
    
    def _get_model(self, model_type: str, hyperparams: Optional[Dict[str, Any]] = None) -> Any:
        """
        모델 인스턴스 생성
        
        Args:
            model_type: 모델 유형
            hyperparams: 하이퍼파라미터
            
        Returns:
            Any: 모델 인스턴스
        """
        if hyperparams is None:
            hyperparams = {}
            
        if model_type == 'lightgbm':
            default_params = {
                'objective': 'binary',
                'metric': 'auc',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1
            }
            params = {**default_params, **hyperparams}
            return lgb.LGBMClassifier(**params)
            
        elif model_type == 'xgboost':
            default_params = {
                'objective': 'binary:logistic',
                'eval_metric': 'auc',
                'eta': 0.05,
                'max_depth': 6,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'verbosity': 0
            }
            params = {**default_params, **hyperparams}
            return xgb.XGBClassifier(**params)
            
        elif model_type == 'random_forest':
            default_params = {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 2,
                'min_samples_leaf': 1,
                'random_state': 42
            }
            params = {**default_params, **hyperparams}
            return RandomForestClassifier(**params)
            
        elif model_type == 'gradient_boosting':
            default_params = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 3,
                'min_samples_split': 2,
                'min_samples_leaf': 1,
                'random_state': 42
            }
            params = {**default_params, **hyperparams}
            return GradientBoostingClassifier(**params)
            
        elif model_type == 'logistic_regression':
            default_params = {
                'C': 1.0,
                'penalty': 'l2',
                'solver': 'liblinear',
                'random_state': 42
            }
            params = {**default_params, **hyperparams}
            return LogisticRegression(**params)
            
        else:
            raise ValueError(f"지원되지 않는 모델 유형: {model_type}")
    
    def _calculate_metrics(
        self, 
        y_true: pd.Series, 
        y_pred: np.ndarray, 
        y_prob: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        평가 지표 계산
        
        Args:
            y_true: 실제 값
            y_pred: 예측 값
            y_prob: 예측 확률
            
        Returns:
            Dict[str, float]: 평가 지표
        """
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0)
        }
        
        if y_prob is not None:
            metrics['auc'] = roc_auc_score(y_true, y_prob)
            
        return metrics
    
    def _calculate_feature_importance(self, model: Any, feature_names: pd.Index) -> Dict[str, float]:
        """
        특성 중요도 계산
        
        Args:
            model: 학습된 모델
            feature_names: 특성 이름
            
        Returns:
            Dict[str, float]: 특성별 중요도
        """
        importances = {}
        
        if hasattr(model, 'feature_importances_'):
            # Tree 기반 모델
            importances = dict(zip(feature_names, model.feature_importances_))
        elif hasattr(model, 'coef_'):
            # 선형 모델
            importances = dict(zip(feature_names, np.abs(model.coef_[0])))
        elif hasattr(model, 'feature_importance'):
            # LightGBM
            importances = dict(zip(feature_names, model.feature_importance()))
        elif hasattr(model, 'get_booster'):
            # XGBoost
            importances = dict(zip(feature_names, model.get_booster().get_score(importance_type='gain')))
            
        return importances
    
    def _calculate_shap_values(self, model: Any, X: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        SHAP 값 계산
        
        Args:
            model: 학습된 모델
            X: 특성 데이터프레임
            
        Returns:
            Optional[Dict[str, Any]]: SHAP 값 정보
        """
        try:
            # 샘플 수가 많은 경우 일부만 사용
            sample_size = min(100, len(X))
            X_sample = X.sample(sample_size, random_state=42)
            
            if isinstance(model, lgb.LGBMClassifier):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_sample)
                
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]  # 이진 분류의 경우 양성 클래스 선택
                    
                return {
                    'values': shap_values,
                    'expected_value': explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value,
                    'data': X_sample
                }
                
            elif isinstance(model, xgb.XGBClassifier):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_sample)
                
                return {
                    'values': shap_values,
                    'expected_value': explainer.expected_value,
                    'data': X_sample
                }
                
            elif isinstance(model, (RandomForestClassifier, GradientBoostingClassifier)):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_sample)
                
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]  # 이진 분류의 경우 양성 클래스 선택
                    
                return {
                    'values': shap_values,
                    'expected_value': explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value,
                    'data': X_sample
                }
                
            elif isinstance(model, LogisticRegression):
                explainer = shap.LinearExplainer(model, X_sample)
                shap_values = explainer.shap_values(X_sample)
                
                return {
                    'values': shap_values,
                    'expected_value': explainer.expected_value,
                    'data': X_sample
                }
                
            else:
                logger.warning(f"지원되지 않는 모델 유형에 대한 SHAP 값 계산: {type(model)}")
                return None
                
        except Exception as e:
            logger.error(f"SHAP 값 계산 중 오류 발생: {str(e)}")
            return None
    
    def _save_model(self, model_key: str, model_info: Dict[str, Any]) -> None:
        """
        모델 저장
        
        Args:
            model_key: 모델 키
            model_info: 모델 정보
        """
        try:
            # 모델 파일 경로
            model_path = os.path.join(self.model_dir, f"{model_key}.joblib")
            
            # 저장할 정보 복사
            save_info = model_info.copy()
            
            # SHAP 값은 크기가 클 수 있으므로 필요시 제외
            if 'shap_values' in save_info:
                # SHAP 값 별도 저장
                shap_path = os.path.join(self.model_dir, f"{model_key}_shap.joblib")
                joblib.dump(save_info['shap_values'], shap_path)
                save_info['shap_values'] = f"{model_key}_shap.joblib"
            
            # 모델 저장
            joblib.dump(save_info, model_path)
            logger.info(f"모델 저장 완료: {model_path}")
            
        except Exception as e:
            logger.error(f"모델 저장 중 오류 발생: {str(e)}")
    
    def load_model(self, model_key: str) -> Optional[Dict[str, Any]]:
        """
        모델 로드
        
        Args:
            model_key: 모델 키
            
        Returns:
            Optional[Dict[str, Any]]: 모델 정보
        """
        try:
            # 모델 파일 경로
            model_path = os.path.join(self.model_dir, f"{model_key}.joblib")
            
            # 모델 로드
            model_info = joblib.load(model_path)
            
            # SHAP 값 로드
            if isinstance(model_info.get('shap_values'), str):
                shap_path = os.path.join(self.model_dir, model_info['shap_values'])
                if os.path.exists(shap_path):
                    model_info['shap_values'] = joblib.load(shap_path)
                else:
                    model_info['shap_values'] = None
            
            # 모델 정보 저장
            self.models[model_key] = model_info
            
            return model_info
            
        except Exception as e:
            logger.error(f"모델 로드 중 오류 발생: {str(e)}")
            return None
    
    def tune_hyperparameters(
        self, 
        X: pd.DataFrame, 
        y: pd.Series, 
        model_type: str = 'lightgbm',
        param_grid: Optional[Dict[str, List[Any]]] = None,
        cv: int = 5,
        scoring: str = 'roc_auc',
        n_iter: int = 20,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        하이퍼파라미터 튜닝
        
        Args:
            X: 특성 데이터프레임
            y: 타겟 변수
            model_type: 모델 유형
            param_grid: 하이퍼파라미터 그리드
            cv: 교차 검증 폴드 수
            scoring: 평가 지표
            n_iter: 랜덤 서치 반복 횟수
            random_state: 랜덤 시드
            
        Returns:
            Dict[str, Any]: 튜닝 결과
        """
        # 기본 모델 가져오기
        base_model = self._get_model(model_type)
        
        # 기본 파라미터 그리드 설정
        if param_grid is None:
            if model_type == 'lightgbm':
                param_grid = {
                    'num_leaves': [15, 31, 63],
                    'learning_rate': [0.01, 0.05, 0.1],
                    'n_estimators': [100, 200, 300],
                    'feature_fraction': [0.7, 0.8, 0.9],
                    'bagging_fraction': [0.7, 0.8, 0.9],
                    'bagging_freq': [3, 5, 7]
                }
            elif model_type == 'xgboost':
                param_grid = {
                    'max_depth': [3, 6, 9],
                    'eta': [0.01, 0.05, 0.1],
                    'n_estimators': [100, 200, 300],
                    'subsample': [0.7, 0.8, 0.9],
                    'colsample_bytree': [0.7, 0.8, 0.9]
                }
            elif model_type == 'random_forest':
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [5, 10, 15],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
            elif model_type == 'gradient_boosting':
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.05, 0.1],
                    'max_depth': [2, 3, 4],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
            elif model_type == 'logistic_regression':
                param_grid = {
                    'C': [0.01, 0.1, 1.0, 10.0],
                    'penalty': ['l1', 'l2'],
                    'solver': ['liblinear']
                }
            else:
                raise ValueError(f"지원되지 않는 모델 유형: {model_type}")
        
        # 랜덤 서치 수행
        random_search = RandomizedSearchCV(
            base_model,
            param_distributions=param_grid,
            n_iter=n_iter,
            cv=cv,
            scoring=scoring,
            random_state=random_state,
            n_jobs=-1
        )
        
        random_search.fit(X, y)
        
        # 최적 파라미터 및 결과 반환
        result = {
            'best_params': random_search.best_params_,
            'best_score': random_search.best_score_,
            'cv_results': random_search.cv_results_
        }
        
        return result
    
    def create_target_variable(
        self, 
        df: pd.DataFrame, 
        product_type: str = 'deposit',
        target_config: Optional[Dict[str, Any]] = None
    ) -> pd.Series:
        """
        타겟 변수 생성
        
        Args:
            df: 입력 데이터프레임
            product_type: 상품 유형
            target_config: 타겟 변수 생성 설정
            
        Returns:
            pd.Series: 타겟 변수
        """
        if target_config is None:
            target_config = {}
            
        # 상품 유형별 타겟 변수 생성 로직
        if product_type == 'deposit':
            # 예금 상품 가입 가능성 타겟
            # 예: 저축 성향이 높은 고객 (잔액 증가율이 높은 고객)
            threshold = target_config.get('threshold', 0.5)
            
            if 'financial_health_score' in df.columns:
                # 금융 건강 점수가 높은 고객
                target = (df['financial_health_score'] > 70).astype(int)
            elif 'vip_score' in df.columns and 'avg_growth_rate' in df.columns:
                # VIP 고객이면서 성장률이 높은 고객
                target = ((df['vip_score'] > 5) & (df['avg_growth_rate'] > 0)).astype(int)
            elif 'bal_B0M' in df.columns and 'amt_credit_limit_use' in df.columns:
                # 잔액 대비 한도 비율이 낮은 고객 (여유 자금이 있는 고객)
                ratio = df['bal_B0M'] / df['amt_credit_limit_use'].replace(0, 1)
                target = (ratio < threshold).astype(int)
            else:
                # 기본값: 랜덤 타겟 (실제 구현에서는 사용하지 않음)
                logger.warning("적절한 특성이 없어 랜덤 타겟 변수를 생성합니다.")
                target = pd.Series(np.random.binomial(1, 0.3, size=len(df)), index=df.index)
                
        elif product_type == 'loan':
            # 대출 상품 가입 가능성 타겟
            # 예: 현금서비스 이용률이 높은 고객
            threshold = target_config.get('threshold', 0.3)
            
            if 'cash_advance_preference' in df.columns:
                # 현금서비스 선호도가 높은 고객
                target = (df['cash_advance_preference'] > threshold).astype(int)
            elif 'bal_ca_B0M' in df.columns and 'bal_B0M' in df.columns:
                # 현금서비스 이용 비중이 높은 고객
                ratio = df['bal_ca_B0M'] / df['bal_B0M'].replace(0, 1)
                target = (ratio > threshold).astype(int)
            elif 'credit_risk_score' in df.columns:
                # 신용 리스크 점수가 중간 이상인 고객
                target = (df['credit_risk_score'] > 0.4).astype(int)
            else:
                # 기본값: 랜덤 타겟 (실제 구현에서는 사용하지 않음)
                logger.warning("적절한 특성이 없어 랜덤 타겟 변수를 생성합니다.")
                target = pd.Series(np.random.binomial(1, 0.2, size=len(df)), index=df.index)
                
        elif product_type == 'fund':
            # 펀드 상품 가입 가능성 타겟
            # 예: VIP 고객이면서 리스크 감수 성향이 있는 고객
            
            if 'vip_score' in df.columns and 'financial_health_score' in df.columns:
                # VIP 고객이면서 금융 건강 점수가 높은 고객
                target = ((df['vip_score'] > 5) & (df['financial_health_score'] > 70)).astype(int)
            elif 'customer_segment' in df.columns:
                # 특정 고객 세그먼트 (예: 세그먼트 0, 2가 투자 성향이 높다고 가정)
                target = df['customer_segment'].isin([0, 2]).astype(int)
            elif 'vip_score' in df.columns and 'age' in df.columns:
                # VIP 고객이면서 젊은 고객 (리스크 감수 성향이 높다고 가정)
                target = ((df['vip_score'] > 5) & (df['age'].astype(int) < 40)).astype(int)
            else:
                # 기본값: 랜덤 타겟 (실제 구현에서는 사용하지 않음)
                logger.warning("적절한 특성이 없어 랜덤 타겟 변수를 생성합니다.")
                target = pd.Series(np.random.binomial(1, 0.1, size=len(df)), index=df.index)
                
        else:
            raise ValueError(f"지원되지 않는 상품 유형: {product_type}")
            
        return target
