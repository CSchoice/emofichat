"""
금융 특성 공학 모듈

금융 데이터에서 고급 특성을 생성하고 선택하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

class FinancialFeatureGenerator:
    """금융 특성 생성기 클래스"""
    
    def __init__(self):
        """금융 특성 생성기 초기화"""
        self.feature_selectors = {}
        self.pca_models = {}
        self.cluster_models = {}
        
    def generate_financial_health_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        금융 건강 관련 특성 생성
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 특성이 추가된 데이터프레임
        """
        result_df = df.copy()
        
        # 1. 부채 비율 (Debt Ratio)
        if all(col in df.columns for col in ['bal_B0M', 'amt_credit_limit_use']):
            result_df['debt_ratio'] = df['bal_B0M'] / df['amt_credit_limit_use'].replace(0, 1)
            # 부채 비율 구간화
            result_df['debt_ratio_level'] = pd.cut(
                result_df['debt_ratio'], 
                bins=[0, 0.3, 0.5, 0.7, 1.0, float('inf')],
                labels=[1, 2, 3, 4, 5]
            ).astype(int)
            
        # 2. 금융 건강 점수 (Financial Health Score)
        # 여러 지표를 결합하여 0-100 사이의 점수 생성
        health_features = []
        
        # 신용 한도 활용도 (낮을수록 좋음)
        if all(col in df.columns for col in ['bal_B0M', 'amt_credit_limit_use']):
            credit_utilization = df['bal_B0M'] / df['amt_credit_limit_use'].replace(0, 1)
            credit_utilization_score = 100 * (1 - np.clip(credit_utilization, 0, 1))
            health_features.append(credit_utilization_score)
            
        # 현금서비스 의존도 (낮을수록 좋음)
        if all(col in df.columns for col in ['bal_ca_B0M', 'bal_B0M']):
            cash_advance_ratio = df['bal_ca_B0M'] / df['bal_B0M'].replace(0, 1)
            cash_advance_score = 100 * (1 - np.clip(cash_advance_ratio, 0, 1))
            health_features.append(cash_advance_score)
            
        # 카드론 의존도 (낮을수록 좋음)
        if all(col in df.columns for col in ['bal_cl_B0M', 'bal_B0M']):
            card_loan_ratio = df['bal_cl_B0M'] / df['bal_B0M'].replace(0, 1)
            card_loan_score = 100 * (1 - np.clip(card_loan_ratio, 0, 1))
            health_features.append(card_loan_score)
            
        # VIP 등급 (높을수록 좋음)
        if 'vip_score' in df.columns:
            vip_score = df['vip_score'] * 10  # 1-10 -> 10-100
            health_features.append(vip_score)
            
        # 성장률 (높을수록 좋음)
        if 'avg_growth_rate' in df.columns:
            growth_score = 50 + df['avg_growth_rate'] * 50  # 중앙값 50
            growth_score = np.clip(growth_score, 0, 100)
            health_features.append(growth_score)
            
        # 금융 건강 점수 계산 (가중 평균)
        if health_features:
            # 모든 특성에 동일한 가중치 부여
            result_df['financial_health_score'] = sum(health_features) / len(health_features)
            
            # 금융 건강 등급 부여
            result_df['financial_health_grade'] = pd.cut(
                result_df['financial_health_score'], 
                bins=[0, 20, 40, 60, 80, 100],
                labels=['F', 'D', 'C', 'B', 'A']
            )
            
        return result_df
    
    def generate_behavioral_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        행동 패턴 관련 특성 생성
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 특성이 추가된 데이터프레임
        """
        result_df = df.copy()
        
        # 1. 할부 선호도 (Installment Preference)
        if all(col in df.columns for col in ['bal_int_B0M', 'bal_pif_B0M']):
            installment_pref = df['bal_int_B0M'] / (df['bal_int_B0M'] + df['bal_pif_B0M']).replace(0, 1)
            result_df['installment_preference'] = np.clip(installment_pref, 0, 1)
            
        # 2. 현금서비스 선호도 (Cash Advance Preference)
        if all(col in df.columns for col in ['bal_ca_B0M', 'bal_B0M']):
            ca_pref = df['bal_ca_B0M'] / df['bal_B0M'].replace(0, 1)
            result_df['cash_advance_preference'] = np.clip(ca_pref, 0, 1)
            
        # 3. 채널 활동성 지수 (Channel Activity Index)
        channel_cols = [
            'cnt_ARS_R6M', 'cnt_ARS_menu_R6M', 'day_ARS_R6M', 'mn_ARS_R6M',
            'cnt_ARS_B0M', 'cnt_menu_ARS_B0M', 'day_ARS_B0M'
        ]
        
        if all(col in df.columns for col in channel_cols):
            # 최근 활동에 더 높은 가중치 부여
            result_df['channel_activity_index'] = (
                df['cnt_ARS_B0M'] * 0.4 + 
                df['day_ARS_B0M'] * 0.3 + 
                df['cnt_ARS_R6M'] * 0.2 + 
                df['day_ARS_R6M'] * 0.1
            )
            
            # 활동성 수준 구분
            result_df['channel_activity_level'] = pd.qcut(
                result_df['channel_activity_index'].clip(lower=0), 
                q=5, 
                labels=['very_low', 'low', 'medium', 'high', 'very_high']
            )
            
        # 4. 마케팅 반응성 지수 (Marketing Response Index)
        marketing_cols = [
            'cnt_CL_TM_B0M', 'cnt_RV_TM_B0M', 'cnt_CA_TM_B0M', 'cnt_promotion_TM_B0M',
            'cnt_card_Issue_TM_B0M', 'cnt_ETC_TM_B0M', 'cnt_point_TM_B0M', 'cnt_Insurance_TM_B0M'
        ]
        
        if all(col in df.columns for col in marketing_cols):
            # 총 마케팅 노출 횟수
            result_df['marketing_exposure_total'] = df[marketing_cols].sum(axis=1)
            
            # 마케팅 유형별 선호도
            for col in marketing_cols:
                col_name = col.replace('cnt_', '').replace('_TM_B0M', '')
                result_df[f'{col_name}_preference'] = df[col] / result_df['marketing_exposure_total'].replace(0, 1)
                
        # 5. 결제 행동 특성 (Payment Behavior)
        if 'code_pay' in df.columns:
            # 결제 방법 원-핫 인코딩
            result_df['payment_method_counter'] = 1
            result_df['payment_method_window'] = 1
            result_df['payment_method_cms'] = 1
            
            # 결제 방법에 따라 해당 열에 1 설정
            result_df.loc[df['code_pay'] == '1', 'payment_method_counter'] = 1
            result_df.loc[df['code_pay'] == '2', 'payment_method_window'] = 1
            result_df.loc[df['code_pay'] == '3', 'payment_method_cms'] = 1
            
        return result_df
    
    def generate_risk_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        리스크 관련 특성 생성
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 특성이 추가된 데이터프레임
        """
        result_df = df.copy()
        
        # 1. 신용 리스크 점수 (Credit Risk Score)
        risk_features = []
        
        # 신용 한도 활용도 (높을수록 위험)
        if all(col in df.columns for col in ['bal_B0M', 'amt_credit_limit_use']):
            credit_utilization = df['bal_B0M'] / df['amt_credit_limit_use'].replace(0, 1)
            credit_risk = np.clip(credit_utilization, 0, 1)
            risk_features.append(credit_risk)
            
        # 현금서비스 의존도 (높을수록 위험)
        if all(col in df.columns for col in ['bal_ca_B0M', 'bal_B0M']):
            cash_advance_ratio = df['bal_ca_B0M'] / df['bal_B0M'].replace(0, 1)
            cash_advance_risk = np.clip(cash_advance_ratio, 0, 1)
            risk_features.append(cash_advance_risk)
            
        # 카드론 의존도 (높을수록 위험)
        if all(col in df.columns for col in ['bal_cl_B0M', 'bal_B0M']):
            card_loan_ratio = df['bal_cl_B0M'] / df['bal_B0M'].replace(0, 1)
            card_loan_risk = np.clip(card_loan_ratio, 0, 1)
            risk_features.append(card_loan_risk)
            
        # VIP 등급 (낮을수록 위험)
        if 'vip_score' in df.columns:
            vip_risk = 1 - (df['vip_score'] / 10)  # 0-1 스케일로 변환
            risk_features.append(vip_risk)
            
        # 성장률 (낮을수록 위험)
        if 'avg_growth_rate' in df.columns:
            growth_risk = 0.5 - df['avg_growth_rate'] / 2  # 중앙값 0.5
            growth_risk = np.clip(growth_risk, 0, 1)
            risk_features.append(growth_risk)
            
        # 신용 리스크 점수 계산 (가중 평균)
        if risk_features:
            # 모든 특성에 동일한 가중치 부여
            result_df['credit_risk_score'] = sum(risk_features) / len(risk_features)
            
            # 리스크 등급 부여
            result_df['credit_risk_grade'] = pd.cut(
                result_df['credit_risk_score'], 
                bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                labels=['A', 'B', 'C', 'D', 'F']
            )
            
        # 2. 이탈 리스크 점수 (Churn Risk Score)
        churn_features = []
        
        # 최근 활동 여부 (비활동적일수록 위험)
        if 'channel_activity_index' in df.columns:
            activity_risk = 1 - np.clip(df['channel_activity_index'] / 10, 0, 1)
            churn_features.append(activity_risk)
            
        # 성장률 (낮을수록 위험)
        if 'avg_growth_rate' in df.columns:
            growth_churn_risk = 0.5 - df['avg_growth_rate'] / 2  # 중앙값 0.5
            growth_churn_risk = np.clip(growth_churn_risk, 0, 1)
            churn_features.append(growth_churn_risk)
            
        # 이탈 리스크 점수 계산 (가중 평균)
        if churn_features:
            result_df['churn_risk_score'] = sum(churn_features) / len(churn_features)
            
            # 이탈 리스크 등급 부여
            result_df['churn_risk_grade'] = pd.cut(
                result_df['churn_risk_score'], 
                bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                labels=['A', 'B', 'C', 'D', 'F']
            )
            
        return result_df
    
    def generate_customer_segment_features(self, df: pd.DataFrame, n_clusters: int = 5) -> pd.DataFrame:
        """
        고객 세그먼트 관련 특성 생성
        
        Args:
            df: 입력 데이터프레임
            n_clusters: 클러스터 수
            
        Returns:
            pd.DataFrame: 특성이 추가된 데이터프레임
        """
        result_df = df.copy()
        
        # 클러스터링에 사용할 특성 선택
        clustering_features = []
        
        # 금융 건강 점수
        if 'financial_health_score' in df.columns:
            clustering_features.append('financial_health_score')
            
        # 신용 리스크 점수
        if 'credit_risk_score' in df.columns:
            clustering_features.append('credit_risk_score')
            
        # 이탈 리스크 점수
        if 'churn_risk_score' in df.columns:
            clustering_features.append('churn_risk_score')
            
        # 채널 활동성 지수
        if 'channel_activity_index' in df.columns:
            clustering_features.append('channel_activity_index')
            
        # 마케팅 노출 총계
        if 'marketing_exposure_total' in df.columns:
            clustering_features.append('marketing_exposure_total')
            
        # 할부 선호도
        if 'installment_preference' in df.columns:
            clustering_features.append('installment_preference')
            
        # 현금서비스 선호도
        if 'cash_advance_preference' in df.columns:
            clustering_features.append('cash_advance_preference')
            
        # VIP 점수
        if 'vip_score' in df.columns:
            clustering_features.append('vip_score')
            
        # 성장률 평균
        if 'avg_growth_rate' in df.columns:
            clustering_features.append('avg_growth_rate')
            
        # 클러스터링 수행
        if clustering_features:
            # 클러스터링에 사용할 데이터 준비
            cluster_data = df[clustering_features].copy()
            
            # 결측치 처리
            cluster_data = cluster_data.fillna(cluster_data.mean())
            
            # K-means 클러스터링 수행
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            result_df['customer_segment'] = kmeans.fit_predict(cluster_data)
            
            # 클러스터 모델 저장
            self.cluster_models['customer_segment'] = kmeans
            
        return result_df
    
    def select_features(self, df: pd.DataFrame, target: pd.Series, k: int = 20, method: str = 'f_classif') -> pd.DataFrame:
        """
        특성 선택
        
        Args:
            df: 입력 데이터프레임
            target: 타겟 변수
            k: 선택할 특성 수
            method: 특성 선택 방법 ('f_classif' 또는 'mutual_info')
            
        Returns:
            pd.DataFrame: 선택된 특성만 포함된 데이터프레임
        """
        # 특성 선택기 설정
        if method == 'f_classif':
            selector = SelectKBest(f_classif, k=k)
        elif method == 'mutual_info':
            selector = SelectKBest(mutual_info_classif, k=k)
        else:
            raise ValueError(f"지원되지 않는 특성 선택 방법: {method}")
            
        # 특성 선택 수행
        X_new = selector.fit_transform(df, target)
        
        # 선택된 특성 인덱스
        selected_indices = selector.get_support(indices=True)
        
        # 선택된 특성 이름
        selected_features = df.columns[selected_indices].tolist()
        
        # 특성 중요도
        feature_scores = selector.scores_
        
        # 특성 중요도 저장
        self.feature_selectors[method] = {
            'selector': selector,
            'selected_features': selected_features,
            'feature_scores': {df.columns[i]: feature_scores[i] for i in range(len(df.columns))}
        }
        
        # 선택된 특성만 포함된 데이터프레임 반환
        return df[selected_features]
    
    def apply_pca(self, df: pd.DataFrame, n_components: int = 10, name: str = 'default') -> pd.DataFrame:
        """
        PCA 적용
        
        Args:
            df: 입력 데이터프레임
            n_components: 주성분 수
            name: PCA 모델 이름
            
        Returns:
            pd.DataFrame: PCA 결과 데이터프레임
        """
        # PCA 모델 설정
        pca = PCA(n_components=n_components)
        
        # PCA 적용
        pca_result = pca.fit_transform(df)
        
        # PCA 모델 저장
        self.pca_models[name] = {
            'pca': pca,
            'explained_variance_ratio': pca.explained_variance_ratio_,
            'components': pca.components_
        }
        
        # PCA 결과 데이터프레임 생성
        pca_df = pd.DataFrame(
            pca_result,
            columns=[f'PC{i+1}' for i in range(n_components)]
        )
        
        return pca_df
    
    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        모든 특성 생성 파이프라인
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 특성이 추가된 데이터프레임
        """
        # 1. 금융 건강 관련 특성 생성
        df = self.generate_financial_health_features(df)
        
        # 2. 행동 패턴 관련 특성 생성
        df = self.generate_behavioral_features(df)
        
        # 3. 리스크 관련 특성 생성
        df = self.generate_risk_features(df)
        
        # 4. 고객 세그먼트 관련 특성 생성
        df = self.generate_customer_segment_features(df)
        
        return df
