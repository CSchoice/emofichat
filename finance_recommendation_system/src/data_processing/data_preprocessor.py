"""
금융 데이터 전처리 모듈

로드된 금융 데이터를 전처리하고 머신러닝 모델에 사용할 수 있는 형태로 변환하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer

logger = logging.getLogger(__name__)

class FinancialDataPreprocessor:
    """금융 데이터 전처리 클래스"""
    
    def __init__(self):
        """금융 데이터 전처리기 초기화"""
        self.encoders = {}
        self.scalers = {}
        self.imputers = {}
        
        # 범주형 변수 목록
        self.categorical_features = [
            'code_gender', 'code_vip', 'code_topcard_grade', 
            'yn_member_ups', 'yn_ca_member_ups', 'yn_cl_member_ups',
            'yn_credit_pss', 'code_pay', 'code_address_billing',
            'code_billing', 'code_billing2', 'YN_billing_B0M',
            'YN_billing_R3M', 'YN_billing_R6M'
        ]
        
        # 수치형 변수 목록
        self.numerical_features = [
            'age', 'amt_limit_1st', 'amt_credit_limit_use', 'amt_ca_limit',
            'amt_cl_limit_fpbl', 'amt_cl_limit_mpbl', 'rate_ca_interest_dis_bf',
            'rate_cl_interest_dis_bf', 'rate_rv_interest_dis_bf',
            'bal_B0M', 'bal_pif_B0M', 'bal_int_B0M', 'bal_ca_B0M',
            'bal_RV_pif_B0M', 'bal_RV_ca_B0M', 'bal_cl_B0M', 'avg_bal_pif_B0M',
            'cnt_ARS_R6M', 'cnt_ARS_menu_R6M', 'day_ARS_R6M', 'mn_ARS_R6M',
            'mn_elapsed_ARS_R6M', 'cnt_ARS_B0M', 'cnt_menu_ARS_B0M', 'day_ARS_B0M',
            'cnt_CL_TM_B0M', 'cnt_RV_TM_B0M', 'cnt_CA_TM_B0M', 'cnt_promotion_TM_B0M',
            'cnt_card_Issue_TM_B0M', 'cnt_ETC_TM_B0M', 'cnt_point_TM_B0M', 'cnt_Insurance_TM_B0M',
            'ratio_CNT_ccd_B1M', 'ratio_CNT_crsl_B1M', 'ratio_CNT_pif_B1M', 'ratio_CNT_int_B1M',
            'ratio_CNT_ca_B1M', 'ratio_CNT_chk_B1M', 'ratio_CNT_cl_B1M', 'ratio_amt_ccd_B1M'
        ]
        
        # 날짜 변수 목록
        self.date_features = [
            'job_mon', 'date_member_reg', 'date_card_issue', 'date_card_expire', 
            'date_card_cancel', 'date_ca_member_reg', 'date_cl_member_reg'
        ]
        
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        금융 데이터 전처리
        
        Args:
            df: 원본 금융 데이터프레임
            
        Returns:
            pd.DataFrame: 전처리된 데이터프레임
        """
        print("[INFO] 금융 데이터 전처리를 시작합니다.")
        
        # 데이터가 비어있는 경우
        if df.empty:
            print("[WARNING] 전처리할 데이터가 없습니다.")
            return df
        
        # 데이터 복사본 생성
        processed_df = df.copy()
        
        try:
            # 1. 결측치 처리
            processed_df = self.handle_missing_values(processed_df)
            
            # 2. 범주형 변수 인코딩
            processed_df = self.encode_categorical_features(processed_df)
            
            # 3. 수치형 변수 스케일링
            processed_df = self.scale_numerical_features(processed_df)
            
            # 4. 날짜 변수 처리
            processed_df = self.process_date_features(processed_df)
            
            # 5. 불필요한 컬럼 제거
            processed_df = self.remove_unnecessary_columns(processed_df)
            
            print(f"[INFO] 금융 데이터 전처리가 완료되었습니다. 처리된 데이터 크기: {processed_df.shape}")
            return processed_df
            
        except Exception as e:
            print(f"[ERROR] 데이터 전처리 중 오류 발생: {str(e)}")
            # 오류 발생 시 원본 데이터 반환
            return df
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        결측치 처리
        
        Args:
            df: 데이터프레임
            
        Returns:
            pd.DataFrame: 결측치가 처리된 데이터프레임
        """
        # 데이터 복사본 생성
        result_df = df.copy()
        
        # 수치형 변수 결측치 처리 (중앙값으로 대체)
        num_features = [col for col in self.numerical_features if col in result_df.columns]
        if num_features:
            for col in num_features:
                if result_df[col].isnull().sum() > 0:
                    if col not in self.imputers:
                        self.imputers[col] = SimpleImputer(strategy='median')
                        self.imputers[col].fit(result_df[[col]])
                    
                    result_df[col] = self.imputers[col].transform(result_df[[col]])
        
        # 범주형 변수 결측치 처리 (최빈값으로 대체)
        cat_features = [col for col in self.categorical_features if col in result_df.columns]
        if cat_features:
            for col in cat_features:
                if result_df[col].isnull().sum() > 0:
                    if col not in self.imputers:
                        self.imputers[col] = SimpleImputer(strategy='most_frequent')
                        self.imputers[col].fit(result_df[[col]])
                    
                    result_df[col] = self.imputers[col].transform(result_df[[col]])
        
        return result_df
    
    def encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        범주형 변수 인코딩
        
        Args:
            df: 데이터프레임
            
        Returns:
            pd.DataFrame: 인코딩된 데이터프레임
        """
        # 데이터 복사본 생성
        result_df = df.copy()
        
        # 범주형 변수 인코딩 (레이블 인코딩)
        cat_features = [col for col in self.categorical_features if col in result_df.columns]
        if cat_features:
            for col in cat_features:
                if col not in self.encoders:
                    self.encoders[col] = LabelEncoder()
                    # 결측치가 있는 경우 처리
                    non_null_values = result_df[col].dropna()
                    if len(non_null_values) > 0:
                        self.encoders[col].fit(non_null_values)
                
                # 결측치가 있는 경우 처리
                non_null_mask = result_df[col].notna()
                if non_null_mask.any():
                    result_df.loc[non_null_mask, col] = self.encoders[col].transform(
                        result_df.loc[non_null_mask, col]
                    )
        
        return result_df
    
    def scale_numerical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        수치형 변수 스케일링
        
        Args:
            df: 데이터프레임
            
        Returns:
            pd.DataFrame: 스케일링된 데이터프레임
        """
        # 데이터 복사본 생성
        result_df = df.copy()
        
        # 수치형 변수 스케일링 (표준화)
        num_features = [col for col in self.numerical_features if col in result_df.columns]
        if num_features:
            if 'numerical' not in self.scalers:
                self.scalers['numerical'] = StandardScaler()
                self.scalers['numerical'].fit(result_df[num_features])
            
            result_df[num_features] = self.scalers['numerical'].transform(result_df[num_features])
        
        return result_df
    
    def process_date_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        날짜 변수 처리
        
        Args:
            df: 데이터프레임
            
        Returns:
            pd.DataFrame: 날짜 변수가 처리된 데이터프레임
        """
        # 데이터 복사본 생성
        result_df = df.copy()
        
        # 날짜 변수 처리
        date_features = [col for col in self.date_features if col in result_df.columns]
        
        if date_features:
            for col in date_features:
                # 날짜 형식 변환 시도
                try:
                    result_df[col] = pd.to_datetime(result_df[col])
                    
                    # 연도, 월, 일 추출
                    result_df[f"{col}_year"] = result_df[col].dt.year
                    result_df[f"{col}_month"] = result_df[col].dt.month
                    result_df[f"{col}_day"] = result_df[col].dt.day
                    
                    # 기준일로부터의 일수 계산 (현재 날짜 기준)
                    today = datetime.now().date()
                    result_df[f"{col}_days_from_today"] = (today - result_df[col].dt.date).dt.days
                    
                    # 원본 날짜 컬럼 삭제
                    result_df = result_df.drop(columns=[col])
                    
                except Exception as e:
                    print(f"[WARNING] 날짜 변수 '{col}' 처리 중 오류 발생: {str(e)}")
        
        return result_df
    
    def remove_unnecessary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        불필요한 컬럼 제거
        
        Args:
            df: 데이터프레임
            
        Returns:
            pd.DataFrame: 불필요한 컬럼이 제거된 데이터프레임
        """
        # 데이터 복사본 생성
        result_df = df.copy()
        
        # 제거할 컬럼 목록 (ID 컬럼 등)
        columns_to_remove = [
            # 여기에 제거할 컬럼 추가
        ]
        
        # 존재하는 컬럼만 제거
        columns_to_remove = [col for col in columns_to_remove if col in result_df.columns]
        if columns_to_remove:
            result_df = result_df.drop(columns=columns_to_remove)
        
        return result_df
        
        self.date_features = [
            'day_max_base', 'day_max_crsl', 'day_max_ca', 'day_max_cl',
            'day_max_chk', 'day_max_pif', 'day_max_int', 'date_pay'
        ]
        
        # 식별자 변수 목록
        self.id_features = ['member_no', 'job_mon']
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        결측치 처리
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 결측치가 처리된 데이터프레임
        """
        # 수치형 변수 결측치 처리
        for col in self.numerical_features:
            if col in df.columns:
                if col not in self.imputers:
                    self.imputers[col] = SimpleImputer(strategy='median')
                    
                col_values = df[col].values.reshape(-1, 1)
                df[col] = self.imputers[col].fit_transform(col_values)
        
        # 범주형 변수 결측치 처리
        for col in self.categorical_features:
            if col in df.columns:
                df[col] = df[col].fillna('UNKNOWN')
        
        # 날짜 변수 결측치 처리
        for col in self.date_features:
            if col in df.columns:
                df[col] = df[col].fillna('00010101')  # 기본값으로 설정
                
        return df
    
    def encode_categorical_features(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """
        범주형 변수 인코딩
        
        Args:
            df: 입력 데이터프레임
            is_training: 학습 데이터 여부
            
        Returns:
            pd.DataFrame: 인코딩된 데이터프레임
        """
        result_df = df.copy()
        
        for col in self.categorical_features:
            if col in df.columns:
                if is_training or col not in self.encoders:
                    self.encoders[col] = LabelEncoder()
                    result_df[col] = self.encoders[col].fit_transform(df[col])
                else:
                    # 학습 데이터가 아닌 경우 기존 인코더 사용
                    # 새로운 카테고리 처리
                    new_categories = set(df[col].unique()) - set(self.encoders[col].classes_)
                    if new_categories:
                        logger.warning(f"열 '{col}'에 새로운 카테고리가 있습니다: {new_categories}")
                        # 새 카테고리를 가장 빈번한 카테고리로 대체
                        for cat in new_categories:
                            df.loc[df[col] == cat, col] = self.encoders[col].classes_[0]
                    
                    result_df[col] = self.encoders[col].transform(df[col])
                    
        return result_df
    
    def scale_numerical_features(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """
        수치형 변수 스케일링
        
        Args:
            df: 입력 데이터프레임
            is_training: 학습 데이터 여부
            
        Returns:
            pd.DataFrame: 스케일링된 데이터프레임
        """
        result_df = df.copy()
        
        for col in self.numerical_features:
            if col in df.columns:
                if is_training or col not in self.scalers:
                    self.scalers[col] = StandardScaler()
                    result_df[col] = self.scalers[col].fit_transform(df[col].values.reshape(-1, 1))
                else:
                    result_df[col] = self.scalers[col].transform(df[col].values.reshape(-1, 1))
                    
        return result_df
    
    def process_date_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        날짜 변수 처리
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 날짜 변수가 처리된 데이터프레임
        """
        result_df = df.copy()
        current_date = datetime.now()
        
        for col in self.date_features:
            if col in df.columns:
                # 날짜 형식 변환
                try:
                    result_df[f'{col}_dt'] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce')
                    
                    # 날짜 관련 파생 변수 생성
                    result_df[f'{col}_days_diff'] = (current_date - result_df[f'{col}_dt']).dt.days
                    
                    # 원본 날짜 컬럼 삭제
                    result_df = result_df.drop(columns=[col])
                except Exception as e:
                    logger.error(f"날짜 처리 중 오류 발생 ({col}): {str(e)}")
                    # 오류 발생 시 원본 컬럼 유지
                    
        return result_df
    
    def create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        파생 변수 생성
        
        Args:
            df: 입력 데이터프레임
            
        Returns:
            pd.DataFrame: 파생 변수가 추가된 데이터프레임
        """
        result_df = df.copy()
        
        # 1. 신용 한도 대비 잔액 비율
        if 'amt_credit_limit_use' in df.columns and 'bal_B0M' in df.columns:
            result_df['credit_utilization_ratio'] = df['bal_B0M'] / df['amt_credit_limit_use'].replace(0, 1)
            
        # 2. 할부 이용 비중
        if 'bal_int_B0M' in df.columns and 'bal_B0M' in df.columns:
            result_df['installment_ratio'] = df['bal_int_B0M'] / df['bal_B0M'].replace(0, 1)
            
        # 3. 현금서비스 이용 비중
        if 'bal_ca_B0M' in df.columns and 'bal_B0M' in df.columns:
            result_df['cash_advance_ratio'] = df['bal_ca_B0M'] / df['bal_B0M'].replace(0, 1)
            
        # 4. 리볼빙 이용 비중
        if 'bal_RV_pif_B0M' in df.columns and 'bal_RV_ca_B0M' in df.columns and 'bal_B0M' in df.columns:
            result_df['revolving_ratio'] = (df['bal_RV_pif_B0M'] + df['bal_RV_ca_B0M']) / df['bal_B0M'].replace(0, 1)
            
        # 5. 카드론 이용 비중
        if 'bal_cl_B0M' in df.columns and 'bal_B0M' in df.columns:
            result_df['card_loan_ratio'] = df['bal_cl_B0M'] / df['bal_B0M'].replace(0, 1)
            
        # 6. VIP 등급 수치화
        if 'code_vip' in df.columns:
            result_df['vip_score'] = df['code_vip'].apply(
                lambda x: 10 if x in ['01', '02', '03'] else 
                          (7 if x in ['04', '05', '06', '07'] else 
                           3 if x in ['08', '09', '10'] else 1)
            )
            
        # 7. 카드 등급 수치화
        if 'code_topcard_grade' in df.columns:
            result_df['card_grade_score'] = df['code_topcard_grade'].apply(
                lambda x: 4 if x == '4' else 
                          3 if x == '3' else 
                          2 if x == '2' else 
                          1 if x == '1' else 0
            )
            
        # 8. 마케팅 반응 지수
        marketing_cols = [
            'cnt_CL_TM_B0M', 'cnt_RV_TM_B0M', 'cnt_CA_TM_B0M', 'cnt_promotion_TM_B0M',
            'cnt_card_Issue_TM_B0M', 'cnt_ETC_TM_B0M', 'cnt_point_TM_B0M', 'cnt_Insurance_TM_B0M'
        ]
        
        if all(col in df.columns for col in marketing_cols):
            result_df['marketing_exposure_total'] = df[marketing_cols].sum(axis=1)
            
        # 9. 채널 활동성 지수
        channel_cols = [
            'cnt_ARS_R6M', 'cnt_ARS_menu_R6M', 'day_ARS_R6M', 'mn_ARS_R6M',
            'cnt_ARS_B0M', 'cnt_menu_ARS_B0M', 'day_ARS_B0M'
        ]
        
        if all(col in df.columns for col in channel_cols):
            result_df['channel_activity_index'] = (
                df['cnt_ARS_B0M'] * 0.4 + 
                df['day_ARS_B0M'] * 0.3 + 
                df['cnt_ARS_R6M'] * 0.2 + 
                df['day_ARS_R6M'] * 0.1
            )
            
        # 10. 성장률 평균
        growth_cols = [
            'ratio_CNT_ccd_B1M', 'ratio_CNT_crsl_B1M', 'ratio_CNT_pif_B1M',
            'ratio_CNT_int_B1M', 'ratio_CNT_ca_B1M', 'ratio_CNT_chk_B1M',
            'ratio_CNT_cl_B1M', 'ratio_amt_ccd_B1M'
        ]
        
        if all(col in df.columns for col in growth_cols):
            result_df['avg_growth_rate'] = df[growth_cols].mean(axis=1)
            
        return result_df
    
    def preprocess(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """
        데이터 전처리 파이프라인
        
        Args:
            df: 입력 데이터프레임
            is_training: 학습 데이터 여부
            
        Returns:
            pd.DataFrame: 전처리된 데이터프레임
        """
        # 1. 결측치 처리
        df = self.handle_missing_values(df)
        
        # 2. 날짜 변수 처리
        df = self.process_date_features(df)
        
        # 3. 파생 변수 생성
        df = self.create_derived_features(df)
        
        # 4. 범주형 변수 인코딩
        df = self.encode_categorical_features(df, is_training)
        
        # 5. 수치형 변수 스케일링
        df = self.scale_numerical_features(df, is_training)
        
        return df
