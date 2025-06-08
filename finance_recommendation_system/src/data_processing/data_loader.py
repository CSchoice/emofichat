"""
금융 데이터 로더 모듈

다양한 금융 데이터 소스에서 데이터를 로드하고 통합하는 기능을 제공합니다.
"""

import os
import glob
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class FinancialDataLoader:
    """금융 데이터 로더 클래스"""
    
    def __init__(self, data_dir: str = "data"):
        """
        금융 데이터 로더 초기화
        
        Args:
            data_dir: 데이터 디렉토리 경로
        """
        self.data_dir = data_dir
        self.schemas = {
            "회원정보": {
                "usecols": ["job_mon", "member_no", "code_gender", "age", "code_vip", 
                           "code_topcard_grade", "yn_member_ups", "yn_ca_member_ups", 
                           "yn_cl_member_ups", "yn_credit_pss"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "code_gender": str, "age": str,
                    "code_vip": str, "code_topcard_grade": str, "yn_member_ups": str,
                    "yn_ca_member_ups": str, "yn_cl_member_ups": str, "yn_credit_pss": str
                }
            },
            "신용정보": {
                "usecols": ["job_mon", "member_no", "amt_limit_1st", "amt_credit_limit_use", 
                           "amt_ca_limit", "amt_cl_limit_fpbl", "amt_cl_limit_mpbl", 
                           "rate_ca_interest_dis_bf", "rate_cl_interest_dis_bf", "rate_rv_interest_dis_bf"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "amt_limit_1st": float, 
                    "amt_credit_limit_use": float, "amt_ca_limit": float, "amt_cl_limit_fpbl": float,
                    "amt_cl_limit_mpbl": float, "rate_ca_interest_dis_bf": float,
                    "rate_cl_interest_dis_bf": float, "rate_rv_interest_dis_bf": float
                }
            },
            "승인매출정보": {
                "usecols": ["job_mon", "member_no", "day_max_base", "day_max_crsl", 
                           "day_max_ca", "day_max_cl", "day_max_chk", "day_max_pif", 
                           "day_max_int", "cnt_ccd_b0m"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "day_max_base": str, "day_max_crsl": str,
                    "day_max_ca": str, "day_max_cl": str, "day_max_chk": str, "day_max_pif": str,
                    "day_max_int": str, "cnt_ccd_b0m": int
                }
            },
            "청구입금정보": {
                "usecols": ["job_mon", "member_no", "date_pay", "code_pay", 
                           "code_address_billing", "code_billing", "code_billing2", 
                           "YN_billing_B0M", "YN_billing_R3M", "YN_billing_R6M"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "date_pay": str, "code_pay": str,
                    "code_address_billing": str, "code_billing": str, "code_billing2": str,
                    "YN_billing_B0M": str, "YN_billing_R3M": str, "YN_billing_R6M": str
                }
            },
            "잔액정보": {
                "usecols": ["job_mon", "member_no", "bal_B0M", "bal_pif_B0M", 
                           "bal_int_B0M", "bal_ca_B0M", "bal_RV_pif_B0M", 
                           "bal_RV_ca_B0M", "bal_cl_B0M", "avg_bal_pif_B0M"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "bal_B0M": float, "bal_pif_B0M": float,
                    "bal_int_B0M": float, "bal_ca_B0M": float, "bal_RV_pif_B0M": float,
                    "bal_RV_ca_B0M": float, "bal_cl_B0M": float, "avg_bal_pif_B0M": float
                }
            },
            "채널정보": {
                "usecols": ["job_mon", "member_no", "cnt_ARS_R6M", "cnt_ARS_menu_R6M", 
                           "day_ARS_R6M", "mn_ARS_R6M", "mn_elapsed_ARS_R6M", 
                           "cnt_ARS_B0M", "cnt_menu_ARS_B0M", "day_ARS_B0M"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "cnt_ARS_R6M": int, "cnt_ARS_menu_R6M": int,
                    "day_ARS_R6M": int, "mn_ARS_R6M": int, "mn_elapsed_ARS_R6M": int,
                    "cnt_ARS_B0M": int, "cnt_menu_ARS_B0M": int, "day_ARS_B0M": int
                }
            },
            "마케팅정보": {
                "usecols": ["job_mon", "member_no", "cnt_CL_TM_B0M", "cnt_RV_TM_B0M", 
                           "cnt_CA_TM_B0M", "cnt_promotion_TM_B0M", "cnt_card_Issue_TM_B0M", 
                           "cnt_ETC_TM_B0M", "cnt_point_TM_B0M", "cnt_Insurance_TM_B0M"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "cnt_CL_TM_B0M": int, "cnt_RV_TM_B0M": int,
                    "cnt_CA_TM_B0M": int, "cnt_promotion_TM_B0M": int, "cnt_card_Issue_TM_B0M": int,
                    "cnt_ETC_TM_B0M": int, "cnt_point_TM_B0M": int, "cnt_Insurance_TM_B0M": int
                }
            },
            "성과정보": {
                "usecols": ["job_mon", "member_no", "ratio_CNT_ccd_B1M", "ratio_CNT_crsl_B1M", 
                           "ratio_CNT_pif_B1M", "ratio_CNT_int_B1M", "ratio_CNT_ca_B1M", 
                           "ratio_CNT_chk_B1M", "ratio_CNT_cl_B1M", "ratio_amt_ccd_B1M"],
                "dtypes": {
                    "job_mon": str, "member_no": str, "ratio_CNT_ccd_B1M": float, "ratio_CNT_crsl_B1M": float,
                    "ratio_CNT_pif_B1M": float, "ratio_CNT_int_B1M": float, "ratio_CNT_ca_B1M": float,
                    "ratio_CNT_chk_B1M": float, "ratio_CNT_cl_B1M": float, "ratio_amt_ccd_B1M": float
                }
            },
            "개인CB정보": {
                "usecols": ["STDT", "ID", "GENDER", "AGE_BAND", "C1Z001373", 
                           "C1M2B4W03", "C1M2B5W03", "C1Z001386", "C1M210000", "C1M210001"],
                "dtypes": {
                    "STDT": str, "ID": str, "GENDER": str, "AGE_BAND": str, "C1Z001373": float,
                    "C1M2B4W03": float, "C1M2B5W03": float, "C1Z001386": float,
                    "C1M210000": int, "C1M210001": int
                }
            },
            "기업CB정보": {
                "usecols": ["BS_DT", "ID", "SIC_CD_3", "WG_GB", "FNDT_DT", 
                           "EMPE_CNT", "CT_CNTY_GU_CD", "LISTD_DT", "LISTD_ABOL_DT", "FN1_1"],
                "dtypes": {
                    "BS_DT": str, "ID": str, "SIC_CD_3": str, "WG_GB": str, "FNDT_DT": str,
                    "EMPE_CNT": int, "CT_CNTY_GU_CD": str, "LISTD_DT": str,
                    "LISTD_ABOL_DT": str, "FN1_1": float
                }
            },
            "통신카드CB결합정보": {
                "usecols": ["BASE_YM", "CUST_ID", "SEX", "AGE", "JB_TP", 
                           "HOME_ADM", "COM_ADM", "HIGHEND_CD1", "HIGHEND_CD2", "HIGHEND_CD3"],
                "dtypes": {
                    "BASE_YM": str, "CUST_ID": str, "SEX": str, "AGE": str, "JB_TP": str,
                    "HOME_ADM": str, "COM_ADM": str, "HIGHEND_CD1": str,
                    "HIGHEND_CD2": str, "HIGHEND_CD3": str
                }
            }
        }
    
    def validate_schema(self) -> bool:
        """
        데이터 스키마 검증
        
        Returns:
            bool: 스키마 검증 결과
        """
        print("=== Schema Validation 시작 ===")
        is_valid = True
        
        for name, schema in self.schemas.items():
            folder = os.path.join(self.base_dir, name)
            files = sorted(glob.glob(f"{folder}/*.csv"))
            
            if not files:
                print(f"[WARNING] '{name}' 폴더에 CSV 없음")
                continue
                
            try:
                hdr = pd.read_csv(files[0], nrows=0).columns.tolist()
                missing = [c for c in schema["usecols"] if c not in hdr]
                extra = [c for c in hdr if c not in schema["usecols"]]
            except Exception as e:
                print(f"[ERROR] 스키마 검증 중 오류 발생: {str(e)}")
                
            return pd.DataFrame()
        
        # 데이터 파일 목록 확인
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith(('.csv', '.xlsx', '.xls'))]
        
        if not data_files:
            logger.warning(f"데이터 파일이 없습니다: {self.data_dir}")
            return pd.DataFrame()
        
        # 데이터 로드 및 병합
        
    def load_data(self):
        """
        금융 데이터 로드
        
        Returns:
            pd.DataFrame: 로드된 금융 데이터
        """
        # 데이터 디렉토리가 없는 경우 샘플 데이터 생성
        if not os.path.exists(self.data_dir):
            print(f"[INFO] 데이터 디렉토리가 없습니다: {self.data_dir}. 샘플 데이터를 생성합니다.")
            return self._generate_sample_data()
        
        # 데이터 파일 목록 확인
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith(('.csv', '.xlsx', '.xls'))]
        
        if not data_files:
            print(f"[INFO] 데이터 파일이 없습니다: {self.data_dir}. 샘플 데이터를 생성합니다.")
            return self._generate_sample_data()
        
        # 실제 데이터 로드 로직 (파일이 있는 경우)
        try:
            # 여기에 실제 데이터 로드 로직 구현
            # 예시: 모든 CSV 파일 로드 및 병합
            dfs = []
            for file in data_files:
                file_path = os.path.join(self.data_dir, file)
                df = self.load_data_from_file(file_path)
                if not df.empty:
                    dfs.append(df)
            
            if dfs:
                return self.merge_data(dfs)
            else:
                print("[WARNING] 로드된 데이터가 없습니다. 샘플 데이터를 생성합니다.")
                return self._generate_sample_data()
        except Exception as e:
            print(f"[ERROR] 데이터 로드 중 오류 발생: {str(e)}")
            return self._generate_sample_data()
    
    def _generate_sample_data(self):
        """
        샘플 금융 데이터 생성
        
        Returns:
            pd.DataFrame: 생성된 샘플 데이터
        """
        print("[INFO] 샘플 금융 데이터를 생성합니다.")
        
        # 샘플 데이터 크기
        n_samples = 1000
        
        # 고객 ID 생성
        customer_ids = [f"CUST{i:06d}" for i in range(1, n_samples + 1)]
        
        # 기본 정보
        np.random.seed(42)  # 재현성을 위한 시드 설정
        genders = np.random.choice(["M", "F"], size=n_samples)
        ages = np.random.randint(20, 70, size=n_samples)
        incomes = np.random.randint(30000, 150000, size=n_samples)
        credit_scores = np.random.randint(500, 850, size=n_samples)
        
        # 금융 행동
        account_balances = np.random.randint(1000, 100000, size=n_samples)
        credit_card_limits = np.random.randint(5000, 50000, size=n_samples)
        credit_utilization = np.random.uniform(0, 0.8, size=n_samples)
        payment_history = np.random.uniform(0.7, 1.0, size=n_samples)
        
        # VIP 상태 (소득과 계좌 잔액에 기반)
        vip_status = ["VIP" if income > 100000 and balance > 50000 else "REGULAR" 
                     for income, balance in zip(incomes, account_balances)]
        
        # 데이터프레임 생성
        df = pd.DataFrame({
            "customer_id": customer_ids,
            "gender": genders,
            "age": ages,
            "income": incomes,
            "credit_score": credit_scores,
            "account_balance": account_balances,
            "credit_limit": credit_card_limits,
            "credit_utilization": credit_utilization,
            "payment_history": payment_history,
            "vip_status": vip_status
        })
        
        print(f"[INFO] {n_samples}개의 샘플 금융 데이터가 생성되었습니다.")
        return df
        dfs = []
        for file in data_files:
            file_path = os.path.join(self.data_dir, file)
            df = self.load_data_from_file(file_path)
            if not df.empty:
                dfs.append(df)
        
        if not dfs:
            logger.warning("로드된 데이터가 없습니다.")
            return pd.DataFrame()
        
        # 데이터 병합
        merged_df = self.merge_data(dfs)
        
        return merged_df
    
    def load_data_from_file(self, file_path: str) -> pd.DataFrame:
        """파일에서 데이터 로드
        
        Args:
            file_path: 데이터 파일 경로
            
        Returns:
            pd.DataFrame: 로드된 데이터프레임
        """
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                return pd.DataFrame()
            
            # 파일 타입 확인
            file_name = os.path.basename(file_path)
            file_type = file_name.split('.')[-1].lower()
            
            # CSV 파일 로드
            if file_type == 'csv':
                df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
            # Excel 파일 로드
            elif file_type in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            else:
                logger.warning(f"지원되지 않는 파일 형식입니다: {file_type}")
                return pd.DataFrame()
            
            # 스키마 검증 및 변환
            schema_key = file_name.split('.')[0]
            df = self._validate_and_convert_schema(df, schema_key)
            
            logger.info(f"데이터 로드 완료: {file_path}, {df.shape[0]} 행, {df.shape[1]} 열")
            return df
            
        except Exception as e:
            logger.error(f"데이터 로드 중 오류 발생: {str(e)}")
            return pd.DataFrame()
    
    def _validate_and_convert_schema(self, df: pd.DataFrame, schema_key: str) -> pd.DataFrame:
        """스키마 검증 및 변환
        
        Args:
            df: 데이터프레임
            schema_key: 스키마 키
            
        Returns:
            pd.DataFrame: 스키마 변환된 데이터프레임
        """
        # 스키마 가져오기
        schema = self.schemas.get(schema_key, self.schemas.get('default', {}))
        
        # 필수 컬럼 확인 (테이블별로 다를 수 있음)
        if schema_key == '개인CB정보':
            required_cols = ['STDT', 'ID']
        elif schema_key == '기업CB정보':
            required_cols = ['BS_DT', 'ID']
        elif schema_key == '통신카드CB결합정보':
            required_cols = ['BASE_YM', 'CUST_ID']
        elif schema_key == '금융상품':
            required_cols = ['상품코드', '상품명', '상품종류']
        else:
            required_cols = ['job_mon', 'member_no']
            
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"필수 컬럼이 없습니다: {col}, {schema_key}")
        
        # 데이터 타입 변환
        for col, dtype in schema.items():
            if col in df.columns:
                try:
                    if dtype == 'str':
                        df[col] = df[col].astype(str)
                    elif dtype == 'int':
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                    elif dtype == 'float':
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
                except Exception as e:
                    logger.warning(f"데이터 타입 변환 중 오류 발생: {col}, {dtype}, {str(e)}")
        
        return df
    
    def merge_data(self, dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """데이터프레임 병합
        
        Args:
            dfs: 데이터프레임 리스트
            
        Returns:
            pd.DataFrame: 병합된 데이터프레임
        """
        if not dfs:
            return pd.DataFrame()
        
        # 회원 정보 테이블 찾기 (기준 테이블)
        member_df = None
        for df in dfs:
            if 'member_no' in df.columns and 'code_gender' in df.columns:
                member_df = df
                break
        
        # 회원 정보 테이블이 없으면 첫 번째 데이터프레임 사용
        if member_df is None:
            member_df = dfs[0].copy()
        else:
            # 회원 정보 테이블을 리스트에서 제거
            dfs = [df for df in dfs if id(df) != id(member_df)]
        
        # 병합 키 매핑 (테이블별 다른 키 컬럼 처리)
        key_mapping = {
            '개인CB정보': {'STDT': 'job_mon', 'ID': 'member_no'},
            '기업CB정보': {'BS_DT': 'job_mon', 'ID': 'member_no'},
            '통신카드CB결합정보': {'BASE_YM': 'job_mon', 'CUST_ID': 'member_no'}
        }
        
        # 각 데이터프레임 병합
        merged_df = member_df.copy()
        
        for df in dfs:
            # 테이블 유형 식별
            table_type = self._identify_table_type(df)
            
            # 병합 키 설정
            if table_type in key_mapping:
                # 키 컬럼 이름 변경
                df_copy = df.copy()
                for src_col, dst_col in key_mapping[table_type].items():
                    if src_col in df_copy.columns:
                        df_copy[dst_col] = df_copy[src_col]
                merge_keys = ['member_no']
            else:
                df_copy = df
                merge_keys = ['member_no', 'job_mon'] if 'job_mon' in df.columns and 'job_mon' in merged_df.columns else ['member_no']
            
            # 병합 키가 있는지 확인
            if all(key in df_copy.columns for key in merge_keys) and all(key in merged_df.columns for key in merge_keys):
                # 중복 컬럼 처리 (키 컬럼 제외)
                duplicate_cols = [col for col in df_copy.columns if col in merged_df.columns and col not in merge_keys]
                for col in duplicate_cols:
                    df_copy = df_copy.rename(columns={col: f"{col}_{table_type}"})
                
                # 데이터프레임 병합
                merged_df = pd.merge(merged_df, df_copy, on=merge_keys, how='outer')
            else:
                logger.warning(f"병합 키가 없어 병합하지 않습니다: {merge_keys}")
        
        return merged_df
    
    def _identify_table_type(self, df: pd.DataFrame) -> str:
        """테이블 유형 식별
        
        Args:
            df: 데이터프레임
            
        Returns:
            str: 테이블 유형
        """
        # 컬럼명으로 테이블 유형 식별
        if 'STDT' in df.columns and 'ID' in df.columns and 'GENDER' in df.columns:
            return '개인CB정보'
        elif 'BS_DT' in df.columns and 'ID' in df.columns and 'SIC_CD_3' in df.columns:
            return '기업CB정보'
        elif 'BASE_YM' in df.columns and 'CUST_ID' in df.columns and 'HIGHEND_CD1' in df.columns:
            return '통신카드CB결합정보'
        elif 'code_gender' in df.columns and 'code_vip' in df.columns:
            return '회원정보'
        elif 'amt_credit_limit_use' in df.columns:
            return '신용정보'
        elif 'bal_B0M' in df.columns and 'bal_ca_B0M' in df.columns:
            return '잔액정보'
        elif 'day_max_base' in df.columns:
            return '승인매출정보'
        elif 'code_pay' in df.columns and 'code_billing' in df.columns:
            return '청구입금정보'
        elif 'cnt_ARS_R6M' in df.columns:
            return '채널정보'
        elif 'cnt_CL_TM_B0M' in df.columns:
            return '마케팅정보'
        elif 'ratio_CNT_ccd_B1M' in df.columns:
            return '성과정보'
        elif '상품코드' in df.columns and '상품명' in df.columns:
            return '금융상품'
        else:
            return 'unknown'
