"""
금융 상품 추천 서비스

사용자의 감정 상태, 재무 상태, 선호도 등을 고려하여 적합한 금융 상품을 추천합니다.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import select, and_, or_, text
from random import sample

from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel
# 필요한 금융 상품 모델 추가 import

# 로거 설정
logger = logging.getLogger(__name__)

# 상품 타입 정의
PRODUCT_TYPE_DEPOSIT = "deposit"  # 예금/적금
PRODUCT_TYPE_FUND = "fund"        # 펀드

async def recommend_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    product_type: Optional[str] = None,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    사용자 정보와 감정 상태를 기반으로 금융 상품을 추천합니다.
    
    Args:
        user_id: 사용자 ID
        user_data: 사용자 재무 데이터
        emotion_data: 감정 분석 결과
        product_type: 상품 유형 (deposit: 예금/적금, fund: 펀드)
        limit: 추천할 상품 개수
        
    Returns:
        추천 상품 목록
    """
    try:
        # 상품 타입이 지정되지 않으면 사용자 상태에 따라 결정
        if not product_type:
            product_type = _determine_product_type(user_data, emotion_data)
            
        # 상품 타입에 따라 다른 추천 로직 실행
        if product_type == PRODUCT_TYPE_DEPOSIT:
            return await recommend_deposit_products(user_id, user_data, emotion_data, limit)
        elif product_type == PRODUCT_TYPE_FUND:
            return await recommend_fund_products(user_id, user_data, emotion_data, limit)
        else:
            logger.warning(f"지원하지 않는 상품 타입: {product_type}")
            return []
            
    except Exception as e:
        logger.error(f"상품 추천 중 오류 발생: {str(e)}")
        return []

def _determine_product_type(user_data: Dict[str, Any], emotion_data: Dict[str, Any]) -> str:
    """
    사용자 상태에 따라 적절한 상품 타입을 결정합니다.
    
    Args:
        user_data: 사용자 재무 데이터
        emotion_data: 감정 분석 결과
        
    Returns:
        추천할 상품 타입 (deposit 또는 fund)
    """
    # 기본값은 예금/적금 상품
    product_type = PRODUCT_TYPE_DEPOSIT
    
    # 위험 회피 성향 판단
    risk_averse = False
    
    # 감정 상태가 불안/걱정/공포인 경우 위험 회피 경향
    if emotion_data:
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        if dominant_emotion in ["공포", "걱정", "슬픔"] or emotion_data.get("is_anxious", False):
            risk_averse = True
    
    # 재무 상태가 불안정한 경우 위험 회피 경향
    financial_health = user_data.get("재정건전성", "정보없음")
    if financial_health in ["주의 필요", "위험", "매우 위험"]:
        risk_averse = True
        
    # 유동성 점수가 낮은 경우 위험 회피 경향
    liquidity_score = user_data.get("유동성점수", 50.0)
    if liquidity_score < 40:
        risk_averse = True
        
    # 연체 이력이 있는 경우 위험 회피 경향
    if user_data.get("연체여부", False):
        risk_averse = True
    
    # 위험 회피 성향이 높으면 예금/적금 상품 추천
    if risk_averse:
        return PRODUCT_TYPE_DEPOSIT
    
    # 감정이 행복하고 재무상태가 양호한 경우 펀드 상품 추천
    if dominant_emotion == "행복" and financial_health in ["양호", "좋음", "매우 좋음"]:
        return PRODUCT_TYPE_FUND
    
    # 재무상태가 좋고 유동성 점수가 높은 경우 펀드 상품 추천
    if financial_health in ["양호", "좋음", "매우 좋음"] and liquidity_score > 70:
        return PRODUCT_TYPE_FUND
    
    # 나이가 젊고 재무상태가 안정적인 경우 펀드 상품 추천
    age = user_data.get("나이", 35)
    if 20 <= age <= 40 and financial_health not in ["주의 필요", "위험", "매우 위험"]:
        return PRODUCT_TYPE_FUND
        
    return product_type

async def recommend_deposit_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    예금/적금 상품을 추천합니다.
    
    Args:
        user_id: 사용자 ID
        user_data: 사용자 재무 데이터
        emotion_data: 감정 분석 결과
        limit: 추천할 상품 개수
        
    Returns:
        추천 상품 목록
    """
    try:
        async with SessionMaker() as session:
            # 사용자 맞춤 추천 로직 구현
            # 1. 연령대에 따른 추천
            age = user_data.get("나이", 35)
            age_condition = ""
            
            if age < 19:
                age_condition = "가입대상고객_조건 LIKE '%어린이%' OR 가입대상고객_조건 LIKE '%청소년%'"
            elif 19 <= age < 24:
                age_condition = "가입대상고객_조건 LIKE '%대학생%' OR 가입대상고객_조건 LIKE '%청년%'"
            elif 24 <= age < 35:
                age_condition = "가입대상고객_조건 LIKE '%사회초년생%' OR 가입대상고객_조건 LIKE '%청년%'"
            elif 65 <= age:
                age_condition = "가입대상고객_조건 LIKE '%시니어%' OR 가입대상고객_조건 LIKE '%노인%' OR 가입대상고객_조건 LIKE '%은퇴%'"
            
            # 2. 감정 상태에 따른 조정
            emotion_condition = ""
            if emotion_data:
                dominant_emotion = emotion_data.get("dominant_emotion", "중립")
                
                # 불안/걱정 감정인 경우 안정적인 상품 우선
                if dominant_emotion in ["공포", "걱정", "슬픔"] or emotion_data.get("is_anxious", False):
                    emotion_condition = "예금입출금방식 = '정기예금' AND 기본금리 >= 3.0"
                # 행복/중립 감정인 경우 다양한 상품 추천
                elif dominant_emotion in ["행복", "중립"]:
                    emotion_condition = "우대금리조건여부 = 'Y' AND 최대우대금리 > 0"
            
            # 3. 재무 상태에 따른 조정
            financial_condition = ""
            liquidity_score = user_data.get("유동성점수", 50.0)
            
            if liquidity_score < 30:
                # 유동성이 낮은 경우 자유입출금식 상품 추천
                financial_condition = "예금입출금방식 = '자유입출금식'"
            elif 30 <= liquidity_score < 70:
                # 보통 유동성인 경우 다양한 상품 추천
                financial_condition = "1=1"  # 모든 상품
            else:
                # 유동성이 높은 경우 장기 상품 추천
                financial_condition = "계약기간개월수_최대구간 >= '12'"
            
            # 4. 통합 쿼리 구성
            conditions = []
            if age_condition:
                conditions.append(f"({age_condition})")
            if emotion_condition:
                conditions.append(f"({emotion_condition})")
            if financial_condition:
                conditions.append(f"({financial_condition})")
            
            # 기본 조건 추가
            conditions.append("기본금리 IS NOT NULL")
            conditions.append("상품명 IS NOT NULL")
            
            # 조건 연결
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 쿼리 실행
            query = text(f"""
                SELECT 
                    은행명, 상품명, 예금입출금방식, 기본금리, 최대우대금리, 
                    계약기간개월수_최소구간, 계약기간개월수_최대구간, 
                    가입금액_최소구간, 가입금액_최대구간, 
                    상품개요_설명
                FROM bank_deposit
                WHERE {where_clause}
                ORDER BY 기본금리 DESC
                LIMIT :limit
            """).bindparams(limit=limit)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            # 결과 포맷팅
            products = []
            for row in rows:
                product = {
                    "은행명": row[0],
                    "상품명": row[1],
                    "상품유형": row[2],
                    "기본금리": row[3],
                    "최대우대금리": row[4],
                    "계약기간": f"{row[5]}~{row[6]}개월",
                    "가입금액": f"{row[7]}~{row[8]}",
                    "설명": row[9]
                }
                products.append(product)
            
            return products if products else await _get_fallback_deposit_products(limit)
    
    except Exception as e:
        logger.error(f"예금/적금 상품 추천 중 오류 발생: {str(e)}")
        return await _get_fallback_deposit_products(limit)

async def _get_fallback_deposit_products(limit: int = 3) -> List[Dict[str, Any]]:
    """
    기본 예금/적금 상품 목록을 반환합니다. (오류 발생 시 폴백)
    """
    try:
        async with SessionMaker() as session:
            query = text("""
                SELECT 
                    은행명, 상품명, 예금입출금방식, 기본금리, 최대우대금리, 
                    계약기간개월수_최소구간, 계약기간개월수_최대구간, 
                    가입금액_최소구간, 가입금액_최대구간, 
                    상품개요_설명
                FROM bank_deposit
                WHERE 기본금리 IS NOT NULL
                ORDER BY 기본금리 DESC
                LIMIT :limit
            """).bindparams(limit=limit)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            products = []
            for row in rows:
                product = {
                    "은행명": row[0],
                    "상품명": row[1],
                    "상품유형": row[2],
                    "기본금리": row[3],
                    "최대우대금리": row[4],
                    "계약기간": f"{row[5]}~{row[6]}개월",
                    "가입금액": f"{row[7]}~{row[8]}",
                    "설명": row[9]
                }
                products.append(product)
            
            return products
    
    except Exception as e:
        logger.error(f"기본 예금/적금 상품 조회 중 오류: {str(e)}")
        # 하드코딩된 기본 상품 반환
        return [
            {
                "은행명": "일반은행",
                "상품명": "정기예금",
                "상품유형": "정기예금",
                "기본금리": 3.5,
                "최대우대금리": 4.0,
                "계약기간": "12~36개월",
                "가입금액": "100만원~",
                "설명": "안정적인 수익을 제공하는 기본 정기예금 상품입니다."
            },
            {
                "은행명": "일반은행",
                "상품명": "자유적금",
                "상품유형": "적립식",
                "기본금리": 3.2,
                "최대우대금리": 3.8,
                "계약기간": "6~24개월",
                "가입금액": "1만원~",
                "설명": "매월 자유롭게 저축할 수 있는 적금 상품입니다."
            }
        ]

async def recommend_fund_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    펀드 상품을 추천합니다.
    
    Args:
        user_id: 사용자 ID
        user_data: 사용자 재무 데이터
        emotion_data: 감정 분석 결과
        limit: 추천할 상품 개수
        
    Returns:
        추천 상품 목록
    """
    try:
        async with SessionMaker() as session:
            # 사용자 맞춤 추천 로직 구현
            # 1. 연령 및 상황에 따른 위험 선호도 결정
            age = user_data.get("나이", 35)
            risk_preference = ""
            
            # 나이가 젊을수록 위험 선호도 높음
            if age < 30:
                risk_preference = "주식형"
            elif 30 <= age < 45:
                risk_preference = "혼합형"
            elif 45 <= age < 60:
                risk_preference = "채권형"
            else:
                risk_preference = "안정형"
            
            # 2. 감정 상태에 따른 조정
            if emotion_data:
                dominant_emotion = emotion_data.get("dominant_emotion", "중립")
                
                # 불안/걱정 감정인 경우 안정적인 상품으로 조정
                if dominant_emotion in ["공포", "걱정", "슬픔"] or emotion_data.get("is_anxious", False):
                    if risk_preference == "주식형":
                        risk_preference = "혼합형"
                    elif risk_preference == "혼합형":
                        risk_preference = "채권형"
                
                # 행복/중립 감정은 원래 선호도 유지
            
            # 3. 재무 상태에 따른 조정
            liquidity_score = user_data.get("유동성점수", 50.0)
            if liquidity_score < 40:
                # 유동성이 낮은 경우 안정적인 상품으로 조정
                if risk_preference == "주식형":
                    risk_preference = "혼합형"
                elif risk_preference == "혼합형":
                    risk_preference = "채권형"
            
            # 4. 위험 선호도에 따른 펀드 유형 결정
            fund_type_condition = ""
            if risk_preference == "주식형":
                fund_type_condition = "중유형 LIKE '%주식%'"
            elif risk_preference == "혼합형":
                fund_type_condition = "중유형 LIKE '%혼합%' OR 중유형 LIKE '%자산배분%'"
            elif risk_preference == "채권형":
                fund_type_condition = "중유형 LIKE '%채권%'"
            else:
                fund_type_condition = "중유형 LIKE '%MMF%' OR 중유형 LIKE '%채권%'"
            
            # 5. 성과 필터링
            performance_condition = "펀드성과정보_1년 IS NOT NULL"
            
            # 6. 통합 쿼리 구성
            conditions = []
            if fund_type_condition:
                conditions.append(f"({fund_type_condition})")
            if performance_condition:
                conditions.append(f"({performance_condition})")
            
            # 기본 조건 추가
            conditions.append("펀드명 IS NOT NULL")
            
            # 조건 연결
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 쿼리 실행
            query = text(f"""
                SELECT 
                    펀드명, 운용사명, 대유형, 중유형, 소유형,
                    펀드성과정보_1년, 펀드성과정보_6개월, 펀드성과정보_3개월,
                    투자위험등급, 투자전략, 순자산
                FROM 공모펀드상품
                WHERE {where_clause}
                ORDER BY 펀드성과정보_1년 DESC
                LIMIT :limit
            """).bindparams(limit=limit)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            # 결과 포맷팅
            products = []
            for row in rows:
                product = {
                    "펀드명": row[0],
                    "운용사": row[1],
                    "유형": f"{row[2]} > {row[3]} > {row[4]}",
                    "1년수익률": row[5],
                    "6개월수익률": row[6],
                    "3개월수익률": row[7],
                    "위험등급": row[8],
                    "투자전략": row[9],
                    "순자산": row[10]
                }
                products.append(product)
            
            return products if products else await _get_fallback_fund_products(limit)
    
    except Exception as e:
        logger.error(f"펀드 상품 추천 중 오류 발생: {str(e)}")
        return await _get_fallback_fund_products(limit)

async def _get_fallback_fund_products(limit: int = 3) -> List[Dict[str, Any]]:
    """
    기본 펀드 상품 목록을 반환합니다. (오류 발생 시 폴백)
    """
    try:
        async with SessionMaker() as session:
            query = text("""
                SELECT 
                    펀드명, 운용사명, 대유형, 중유형, 소유형,
                    펀드성과정보_1년, 펀드성과정보_6개월, 펀드성과정보_3개월,
                    투자위험등급, 투자전략, 순자산
                FROM 공모펀드상품
                WHERE 펀드성과정보_1년 IS NOT NULL
                ORDER BY 펀드성과정보_1년 DESC
                LIMIT :limit
            """).bindparams(limit=limit)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            products = []
            for row in rows:
                product = {
                    "펀드명": row[0],
                    "운용사": row[1],
                    "유형": f"{row[2]} > {row[3]} > {row[4]}",
                    "1년수익률": row[5],
                    "6개월수익률": row[6],
                    "3개월수익률": row[7],
                    "위험등급": row[8],
                    "투자전략": row[9],
                    "순자산": row[10]
                }
                products.append(product)
            
            return products
    
    except Exception as e:
        logger.error(f"기본 펀드 상품 조회 중 오류: {str(e)}")
        # 하드코딩된 기본 상품 반환
        return [
            {
                "펀드명": "가치주식형펀드",
                "운용사": "표준자산운용",
                "유형": "국내 > 주식형 > 가치주",
                "1년수익률": 12.5,
                "6개월수익률": 6.8,
                "3개월수익률": 3.2,
                "위험등급": 2,
                "투자전략": "국내 우량 가치주에 투자하여 안정적인 수익을 추구합니다.",
                "순자산": 10000000000
            },
            {
                "펀드명": "글로벌채권형펀드",
                "운용사": "표준자산운용",
                "유형": "해외 > 채권형 > 글로벌",
                "1년수익률": 5.5,
                "6개월수익률": 2.8,
                "3개월수익률": 1.2,
                "위험등급": 4,
                "투자전략": "글로벌 국채 및 우량 회사채에 투자하여 안정적인 이자수익을 추구합니다.",
                "순자산": 5000000000
            }
        ]

def format_product_recommendation(
    products: List[Dict[str, Any]], 
    product_type: str, 
    emotion_data: Dict[str, Any] = None
) -> str:
    """
    추천 상품 목록을 사용자 친화적인 텍스트로 포맷팅합니다.
    
    Args:
        products: 추천 상품 목록
        product_type: 상품 유형 (deposit 또는 fund)
        emotion_data: 감정 분석 결과
        
    Returns:
        포맷팅된 추천 메시지
    """
    if not products:
        return "현재 추천할 수 있는 상품이 없습니다."
    
    # 감정에 따른 메시지 톤 조정
    intro_message = "고객님께 맞는 상품을 추천해 드립니다."
    if emotion_data:
        dominant_emotion = emotion_data.get("dominant_emotion", "중립")
        
        if dominant_emotion in ["화남", "슬픔"]:
            intro_message = "현재 상황이 어려우실 수 있지만, 다음 상품들이 도움이 될 수 있을 것 같습니다."
        elif dominant_emotion == "공포" or emotion_data.get("is_anxious", False):
            intro_message = "걱정이 많으신 것 같습니다. 안정적인 상품 위주로 추천해 드립니다."
        elif dominant_emotion == "행복":
            intro_message = "좋은 기분을 더 오래 유지할 수 있는 상품을 추천해 드립니다."
    
    # 상품 타입에 따른 메시지 생성
    if product_type == PRODUCT_TYPE_DEPOSIT:
        message = f"{intro_message}\n\n📌 **예금/적금 상품 추천**\n\n"
        
        for i, product in enumerate(products, 1):
            message += f"{i}. **{product.get('상품명', '정보 없음')}** ({product.get('은행명', '정보 없음')})\n"
            message += f"   - 상품유형: {product.get('상품유형', '정보 없음')}\n"
            message += f"   - 기본금리: {product.get('기본금리', 0)}%"
            
            if product.get('최대우대금리') and product.get('최대우대금리') > product.get('기본금리', 0):
                message += f" (최대 {product.get('최대우대금리')}%)\n"
            else:
                message += "\n"
                
            message += f"   - 계약기간: {product.get('계약기간', '정보 없음')}\n"
            message += f"   - 가입금액: {product.get('가입금액', '정보 없음')}\n"
            
            if product.get('설명'):
                message += f"   - 설명: {product.get('설명')[:100]}...\n"
                
            message += "\n"
    
    elif product_type == PRODUCT_TYPE_FUND:
        message = f"{intro_message}\n\n📌 **펀드 상품 추천**\n\n"
        
        for i, product in enumerate(products, 1):
            message += f"{i}. **{product.get('펀드명', '정보 없음')}** ({product.get('운용사', '정보 없음')})\n"
            message += f"   - 유형: {product.get('유형', '정보 없음')}\n"
            message += f"   - 수익률: 1년 {product.get('1년수익률', 0)}%, 6개월 {product.get('6개월수익률', 0)}%, 3개월 {product.get('3개월수익률', 0)}%\n"
            message += f"   - 위험등급: {product.get('위험등급', '정보 없음')}\n"
            
            if product.get('투자전략'):
                message += f"   - 투자전략: {product.get('투자전략')[:100]}...\n"
                
            message += "\n"
    
    else:
        message = "지원하지 않는 상품 유형입니다."
    
    message += "해당 상품에 관심이 있으시면 더 자세한 정보를 알려드리겠습니다."
    return message
