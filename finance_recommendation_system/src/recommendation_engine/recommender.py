"""
금융 상품 추천 엔진 모듈

학습된 모델을 사용하여 고객에게 금융 상품을 추천하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
import os
import joblib
from datetime import datetime

logger = logging.getLogger(__name__)

class FinancialRecommender:
    """금융 상품 추천 엔진 클래스"""
    
    def __init__(self, model_dir: str = "models", product_db_path: str = "data/financial_products.csv"):
        """
        금융 상품 추천 엔진 초기화
        
        Args:
            model_dir: 모델 디렉토리 경로
            product_db_path: 금융 상품 데이터베이스 경로
        """
        self.model_dir = model_dir
        self.product_db_path = product_db_path
        self.models = {}
        self.products = self._load_products()
        
    def _load_products(self) -> Dict[str, pd.DataFrame]:
        """
        금융 상품 데이터 로드
        
        Returns:
            Dict[str, pd.DataFrame]: 상품 유형별 데이터프레임
        """
        try:
            # 상품 데이터베이스 로드
            if os.path.exists(self.product_db_path):
                df = pd.read_csv(self.product_db_path)
                
                # 상품 유형별로 분류
                products = {}
                
                if '상품종류' in df.columns:
                    # 예금 상품
                    deposit_df = df[df['상품종류'] == '은행수신상품'].copy()
                    if not deposit_df.empty:
                        products['deposit'] = deposit_df
                        
                    # 대출 상품
                    loan_df = df[df['상품종류'] == '은행여신상품'].copy()
                    if not loan_df.empty:
                        products['loan'] = loan_df
                        
                    # 펀드 상품
                    fund_df = df[df['상품종류'] == '펀드상품'].copy()
                    if not fund_df.empty:
                        products['fund'] = fund_df
                        
                    return products
                else:
                    logger.warning("상품 데이터베이스에 '상품종류' 열이 없습니다.")
                    return {}
            else:
                logger.warning(f"상품 데이터베이스 파일이 존재하지 않습니다: {self.product_db_path}")
                return {}
                
        except Exception as e:
            logger.error(f"상품 데이터 로드 중 오류 발생: {str(e)}")
            return {}
    
    def load_model(self, product_type: str, model_type: str = 'lightgbm') -> bool:
        """
        추천 모델 로드
        
        Args:
            product_type: 상품 유형 ('deposit', 'fund', 'loan')
            model_type: 모델 유형 ('lightgbm', 'xgboost', 'random_forest', 'gradient_boosting', 'logistic_regression')
            
        Returns:
            bool: 모델 로드 성공 여부
        """
        model_key = f"{product_type}_{model_type}"
        model_path = os.path.join(self.model_dir, f"{model_key}.joblib")
        
        try:
            if os.path.exists(model_path):
                # 모델 로드
                model_info = joblib.load(model_path)
                self.models[model_key] = model_info
                logger.info(f"모델 로드 성공: {model_path}")
                return True
            else:
                logger.warning(f"모델 파일이 존재하지 않습니다: {model_path}")
                return False
                
        except Exception as e:
            logger.error(f"모델 로드 중 오류 발생: {str(e)}")
            return False
    
    def recommend_products(
        self, 
        customer_data: pd.DataFrame, 
        product_type: str = 'deposit', 
        model_type: str = 'lightgbm',
        top_n: int = 5,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        고객에게 금융 상품 추천
        
        Args:
            customer_data: 고객 데이터
            product_type: 상품 유형 ('deposit', 'fund', 'loan')
            model_type: 모델 유형 ('lightgbm', 'xgboost', 'random_forest', 'gradient_boosting', 'logistic_regression')
            top_n: 추천할 상품 수
            threshold: 추천 확률 임계값
            
        Returns:
            List[Dict[str, Any]]: 추천 상품 목록
        """
        model_key = f"{product_type}_{model_type}"
        
        # 모델이 로드되어 있지 않으면 로드
        if model_key not in self.models:
            if not self.load_model(product_type, model_type):
                logger.error(f"모델을 로드할 수 없습니다: {model_key}")
                return []
        
        model_info = self.models[model_key]
        model = model_info['model']
        feature_names = model_info['feature_names']
        
        # 고객 데이터에서 모델에 필요한 특성만 선택
        customer_features = customer_data[feature_names].copy()
        
        # 예측 확률 계산
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(customer_features)[:, 1]
        else:
            # predict_proba가 없는 경우 predict 결과 사용
            proba = model.predict(customer_features)
        
        # 임계값 이상인 고객만 선택
        eligible_customers = customer_data[proba >= threshold].copy()
        eligible_proba = proba[proba >= threshold]
        
        if eligible_customers.empty:
            logger.info(f"임계값({threshold}) 이상인 고객이 없습니다.")
            return []
        
        # 상품 추천
        recommendations = []
        
        # 상품 데이터베이스에서 해당 유형의 상품 가져오기
        if product_type in self.products:
            products_df = self.products[product_type]
            
            # 각 고객에 대해 상품 점수 계산
            for i, (_, customer) in enumerate(eligible_customers.iterrows()):
                customer_proba = eligible_proba[i]
                
                # 고객 특성에 따른 상품 점수 계산
                product_scores = self._calculate_product_scores(customer, products_df, product_type)
                
                # 최종 점수 = 모델 예측 확률 * 상품 점수
                final_scores = product_scores * customer_proba
                
                # 점수가 높은 상위 N개 상품 선택
                top_products = products_df.iloc[final_scores.argsort()[-top_n:][::-1]]
                
                # 추천 이유 생성
                for _, product in top_products.iterrows():
                    recommendation = {
                        'customer_id': customer.get('member_no', 'unknown'),
                        'product_id': product.get('상품코드', 'unknown'),
                        'product_name': product.get('상품명', 'unknown'),
                        'product_type': product_type,
                        'score': float(final_scores.loc[product.name]),
                        'probability': float(customer_proba),
                        'reasons': self._generate_recommendation_reasons(customer, product, product_type)
                    }
                    recommendations.append(recommendation)
        else:
            logger.warning(f"상품 데이터베이스에 '{product_type}' 유형의 상품이 없습니다.")
        
        return recommendations
    
    def _calculate_product_scores(
        self, 
        customer: pd.Series, 
        products_df: pd.DataFrame, 
        product_type: str
    ) -> pd.Series:
        """
        고객 특성에 따른 상품 점수 계산
        
        Args:
            customer: 고객 데이터
            products_df: 상품 데이터프레임
            product_type: 상품 유형
            
        Returns:
            pd.Series: 상품별 점수
        """
        scores = pd.Series(0.5, index=products_df.index)  # 기본 점수 0.5
        
        if product_type == 'deposit':
            # 예금 상품 점수 계산
            
            # 1. 금융 건강 점수에 따른 점수 조정
            if 'financial_health_score' in customer:
                health_score = customer['financial_health_score']
                
                # 금융 건강 점수가 높은 고객에게는 고금리 상품 추천
                if '최고금리' in products_df.columns:
                    high_rate_products = products_df['최고금리'] > products_df['최고금리'].median()
                    if health_score > 70:
                        scores.loc[high_rate_products] += 0.2
                    elif health_score < 40:
                        scores.loc[~high_rate_products] += 0.1
                
                # 금융 건강 점수가 낮은 고객에게는 단기 상품 추천
                if '계약기간개월수_최대구간' in products_df.columns:
                    short_term_products = products_df['계약기간개월수_최대구간'].astype(float) <= 12
                    if health_score < 40:
                        scores.loc[short_term_products] += 0.2
                    elif health_score > 70:
                        scores.loc[~short_term_products] += 0.1
            
            # 2. 잔액에 따른 점수 조정
            if 'bal_B0M' in customer:
                balance = customer['bal_B0M']
                
                if '가입금액_최소구간' in products_df.columns:
                    # 잔액이 많은 고객에게는 최소 가입금액이 높은 상품 추천
                    high_min_amount_products = products_df['가입금액_최소구간'].astype(float) > 1000000
                    if balance > 10000000:
                        scores.loc[high_min_amount_products] += 0.2
                    elif balance < 1000000:
                        scores.loc[~high_min_amount_products] += 0.2
            
            # 3. VIP 등급에 따른 점수 조정
            if 'vip_score' in customer:
                vip_score = customer['vip_score']
                
                # VIP 고객에게는 프리미엄 상품 추천
                if '상품명' in products_df.columns:
                    premium_products = products_df['상품명'].str.contains('프리미엄|VIP|골드|플래티넘', case=False)
                    if vip_score > 7:
                        scores.loc[premium_products] += 0.3
        
        elif product_type == 'loan':
            # 대출 상품 점수 계산
            
            # 1. 신용 리스크 점수에 따른 점수 조정
            if 'credit_risk_score' in customer:
                risk_score = customer['credit_risk_score']
                
                # 리스크가 낮은 고객에게는 저금리 상품 추천
                if '기본금리' in products_df.columns:
                    low_rate_products = products_df['기본금리'] < products_df['기본금리'].median()
                    if risk_score < 0.3:
                        scores.loc[low_rate_products] += 0.2
                    elif risk_score > 0.7:
                        scores.loc[~low_rate_products] += 0.1
            
            # 2. 현금서비스 선호도에 따른 점수 조정
            if 'cash_advance_preference' in customer:
                ca_pref = customer['cash_advance_preference']
                
                # 현금서비스 선호도가 높은 고객에게는 단기 대출 상품 추천
                if '대출기간' in products_df.columns:
                    short_term_loans = products_df['대출기간'].astype(str).str.contains('1년|12개월', case=False)
                    if ca_pref > 0.5:
                        scores.loc[short_term_loans] += 0.2
        
        elif product_type == 'fund':
            # 펀드 상품 점수 계산
            
            # 1. 금융 건강 점수에 따른 점수 조정
            if 'financial_health_score' in customer:
                health_score = customer['financial_health_score']
                
                # 금융 건강 점수가 높은 고객에게는 주식형 펀드 추천
                if '펀드유형' in products_df.columns:
                    stock_funds = products_df['펀드유형'].str.contains('주식형|혼합형', case=False)
                    bond_funds = products_df['펀드유형'].str.contains('채권형|MMF', case=False)
                    
                    if health_score > 70:
                        scores.loc[stock_funds] += 0.3
                    elif health_score < 40:
                        scores.loc[bond_funds] += 0.3
            
            # 2. 나이에 따른 점수 조정
            if 'age' in customer:
                age = int(customer['age'])
                
                # 젊은 고객에게는 공격적인 펀드, 고령 고객에게는 안정적인 펀드 추천
                if '위험등급' in products_df.columns:
                    high_risk_funds = products_df['위험등급'].astype(str).str.contains('1등급|2등급', case=False)
                    low_risk_funds = products_df['위험등급'].astype(str).str.contains('4등급|5등급', case=False)
                    
                    if age < 40:
                        scores.loc[high_risk_funds] += 0.2
                    elif age > 60:
                        scores.loc[low_risk_funds] += 0.3
        
        return scores
    
    def _generate_recommendation_reasons(
        self, 
        customer: pd.Series, 
        product: pd.Series, 
        product_type: str
    ) -> List[str]:
        """
        추천 이유 생성
        
        Args:
            customer: 고객 데이터
            product: 상품 데이터
            product_type: 상품 유형
            
        Returns:
            List[str]: 추천 이유 목록
        """
        reasons = []
        
        if product_type == 'deposit':
            # 예금 상품 추천 이유
            
            # 1. 금융 건강 점수 관련 이유
            if 'financial_health_score' in customer:
                health_score = customer['financial_health_score']
                
                if health_score > 70:
                    if '최고금리' in product and product['최고금리'] > 2.5:
                        reasons.append(f"고객님의 우수한 금융 건강 상태에 적합한 고금리({product['최고금리']}%) 상품입니다.")
                elif health_score < 40:
                    if '계약기간개월수_최대구간' in product and float(product['계약기간개월수_최대구간']) <= 12:
                        reasons.append("단기 저축으로 유동성을 확보하면서 금융 건강을 개선할 수 있는 상품입니다.")
            
            # 2. 잔액 관련 이유
            if 'bal_B0M' in customer:
                balance = customer['bal_B0M']
                
                if '가입금액_최소구간' in product:
                    min_amount = float(product['가입금액_최소구간'])
                    if balance > 10000000 and min_amount > 1000000:
                        reasons.append("고객님의 잔액 수준에 적합한 고액 예금 상품입니다.")
                    elif balance < 1000000 and min_amount < 100000:
                        reasons.append("소액으로 시작할 수 있는 부담 없는 예금 상품입니다.")
            
            # 3. VIP 등급 관련 이유
            if 'vip_score' in customer:
                vip_score = customer['vip_score']
                
                if vip_score > 7 and '상품명' in product and any(keyword in product['상품명'] for keyword in ['프리미엄', 'VIP', '골드', '플래티넘']):
                    reasons.append("고객님의 VIP 등급에 맞는 프리미엄 예금 상품입니다.")
        
        elif product_type == 'loan':
            # 대출 상품 추천 이유
            
            # 1. 신용 리스크 관련 이유
            if 'credit_risk_score' in customer:
                risk_score = customer['credit_risk_score']
                
                if risk_score < 0.3 and '기본금리' in product and product['기본금리'] < 5:
                    reasons.append(f"고객님의 우수한 신용 상태에 적합한 저금리({product['기본금리']}%) 대출 상품입니다.")
                elif risk_score > 0.7:
                    reasons.append("신용 개선에 도움이 될 수 있는 대출 상품입니다.")
            
            # 2. 현금서비스 선호도 관련 이유
            if 'cash_advance_preference' in customer:
                ca_pref = customer['cash_advance_preference']
                
                if ca_pref > 0.5 and '대출기간' in product and '1년' in str(product['대출기간']):
                    reasons.append("단기 자금 필요 시 현금서비스보다 유리한 금리 조건의 대출 상품입니다.")
        
        elif product_type == 'fund':
            # 펀드 상품 추천 이유
            
            # 1. 금융 건강 점수 관련 이유
            if 'financial_health_score' in customer:
                health_score = customer['financial_health_score']
                
                if health_score > 70 and '펀드유형' in product and '주식형' in product['펀드유형']:
                    reasons.append("고객님의 우수한 금융 상태에 적합한 성장형 펀드 상품입니다.")
                elif health_score < 40 and '펀드유형' in product and '채권형' in product['펀드유형']:
                    reasons.append("안정적인 수익을 추구하는 저위험 펀드 상품입니다.")
            
            # 2. 나이 관련 이유
            if 'age' in customer:
                age = int(customer['age'])
                
                if age < 40 and '위험등급' in product and product['위험등급'] in ['1등급', '2등급']:
                    reasons.append("장기 투자를 통한 높은 수익을 기대할 수 있는 펀드 상품입니다.")
                elif age > 60 and '위험등급' in product and product['위험등급'] in ['4등급', '5등급']:
                    reasons.append("원금 보존을 중시하는 안정적인 펀드 상품입니다.")
        
        # 공통 이유 (상품 유형에 관계없이)
        if not reasons:
            reasons.append(f"고객님의 금융 프로필에 적합한 {product_type} 상품입니다.")
        
        return reasons
