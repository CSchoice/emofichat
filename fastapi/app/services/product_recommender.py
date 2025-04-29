import logging
from typing import Dict, List, Any, Optional

from sqlalchemy import select, text
from app.core.db import SessionMaker
from app.models.finance import User, CardUsage, Delinquency, BalanceInfo, SpendingPattern, ScenarioLabel

from app.services.product_formatter import format_product_recommendation

# 로거 설정
logger = logging.getLogger(__name__)

PRODUCT_TYPE_DEPOSIT = "deposit"  # 예금/적금
PRODUCT_TYPE_FUND = "fund"         # 펀드

# 유틸리티 함수
def format_amount(amount: int) -> str:
    """금액을 한국식으로 포맷팅 (1000 -> 1,000원, 1000000 -> 100만원)"""
    if not amount:
        return ""
    
    if amount >= 10000:
        # 만원 단위로 표시
        man = amount // 10000
        remainder = amount % 10000
        
        if remainder == 0:
            return f"{man:,}만원"
        else:
            return f"{man:,}만 {remainder:,}원"
    else:
        return f"{amount:,}원"

async def get_bank_info(bank_id: int, session) -> dict:
    """은행 ID로 은행 정보 조회"""
    try:
        query = text("SELECT id, name FROM bank WHERE id = :bank_id").bindparams(bank_id=bank_id)
        result = await session.execute(query)
        row = result.fetchone()
        
        if row:
            return {"id": row[0], "name": row[1]}
        else:
            return {"id": None, "name": "알 수 없음"}
    except Exception as e:
        logger.error(f"[get_bank_info] 실패: {e}")
        return {"id": None, "name": "오류 발생"}

async def recommend_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    product_type: Optional[str] = None,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    사용자 정보와 감정 상태를 기반으로 금융 상품을 추천합니다.
    """

    try:
        if not product_type:
            product_type = _determine_product_type(user_data, emotion_data)

        if product_type == PRODUCT_TYPE_DEPOSIT:
            products = await recommend_deposit_products(user_id, user_data, emotion_data, limit)
        elif product_type == PRODUCT_TYPE_FUND:
            products = await recommend_fund_products(user_id, user_data, emotion_data, limit)
        else:
            logger.warning(f"지원하지 않는 상품 타입: {product_type}")
            products = []

        return products

    except Exception as e:
        logger.error(f"[recommend_products] 추천 실패: {e}")
        return []

def _determine_product_type(user_data: Dict[str, Any], emotion_data: Dict[str, Any]) -> str:
    """
    감정, 재무 상태를 고려해 deposit/fund 중 추천할 상품 타입 결정
    """
    dominant_emotion = emotion_data.get("dominant_emotion", "중립") if emotion_data else "중립"
    financial_health = user_data.get("재정건전성", "정보없음")
    liquidity_score = user_data.get("유동성점수", 50.0)
    age = user_data.get("나이", 35)
    is_anxious = emotion_data.get("is_anxious", False) if emotion_data else False

    risk_averse = False

    if dominant_emotion in ["공포", "걱정", "슬픔"] or is_anxious:
        risk_averse = True
    if financial_health in ["주의 필요", "위험", "매우 위험"]:
        risk_averse = True
    if liquidity_score < 40:
        risk_averse = True
    if user_data.get("연체여부", False):
        risk_averse = True

    if risk_averse:
        return PRODUCT_TYPE_DEPOSIT

    if dominant_emotion == "행복" and financial_health in ["양호", "좋음", "매우 좋음"]:
        return PRODUCT_TYPE_FUND
    if financial_health in ["양호", "좋음", "매우 좋음"] and liquidity_score > 70:
        return PRODUCT_TYPE_FUND
    if 20 <= age <= 40 and financial_health not in ["주의 필요", "위험", "매우 위험"]:
        return PRODUCT_TYPE_FUND

    return PRODUCT_TYPE_DEPOSIT

async def recommend_deposit_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    예금/적금 상품 추천
    """

    try:
        logger.debug(f"[recommend_deposit_products] 시작 - user_id: {user_id}, limit: {limit}")
        async with SessionMaker() as session:
            logger.debug("DB 세션 생성 성공")
            conditions = ["기본금리 IS NOT NULL", "상품명 IS NOT NULL"]
            params = {"limit": limit}

            # 연령 필터
            age = user_data.get("나이", 35)
            if age < 19:
                conditions.append("(가입대상고객_조건 LIKE '%어린이%' OR 가입대상고객_조건 LIKE '%청소년%')")
            elif 19 <= age < 24:
                conditions.append("(가입대상고객_조건 LIKE '%대학생%' OR 가입대상고객_조건 LIKE '%청년%')")
            elif 24 <= age < 35:
                conditions.append("(가입대상고객_조건 LIKE '%사회초년생%' OR 가입대상고객_조건 LIKE '%청년%')")
            elif age >= 65:
                conditions.append("(가입대상고객_조건 LIKE '%시니어%' OR 가입대상고객_조건 LIKE '%노인%' OR 가입대상고객_조건 LIKE '%은퇴%')")

            # 감정 필터
            dominant_emotion = emotion_data.get("dominant_emotion", "중립") if emotion_data else "중립"
            if dominant_emotion in ["공포", "걱정", "슬픔"] or emotion_data.get("is_anxious", False):
                conditions.append("(예금입출금방식 = '정기예금' AND 기본금리 >= 3.0)")
            elif dominant_emotion in ["행복", "중립"]:
                conditions.append("(우대금리조건여부 = 'Y' AND 최대우대금리 > 0)")

            # 재무상태 필터
            liquidity_score = user_data.get("유동성점수", 50.0)
            if liquidity_score < 30:
                conditions.append("예금입출금방식 = '자유입출금식'")
            elif liquidity_score >= 70:
                conditions.append("계약기간개월수_최대구간 >= '12'")

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT 
                    은행명, 상품명, 예금입출금방식, 기본금리, 최대우대금리,
                    계약기간개월수_최소구간, 계약기간개월수_최대구간,
                    가입금액_최소구간, 가입금액_최대구간, 상품개요_설명
                FROM bank_deposit
                WHERE {where_clause}
                ORDER BY 기본금리 DESC
                LIMIT :limit
            """).bindparams(**params)
            logger.debug(f"쿼리 생성: {query}")

            try:
                logger.debug("쿼리 실행 시작")
                result = await session.execute(query)
                rows = result.fetchall()
                logger.debug(f"쿼리 실행 성공, {len(rows)}개 결과 조회됨")
            except Exception as exe:
                logger.error(f"쿼리 실행 실패: {exe}")
                raise

            products = []
            for row in rows:
                # 계약기간 포맷팅 개선
                period_min = row[5] if row[5] and row[5] not in ['제한없음', '없음', ''] else None
                period_max = row[6] if row[6] and row[6] not in ['제한없음', '없음', ''] else None
                
                if period_min and period_max and period_min == period_max:
                    period_str = f"{period_min}개월"
                elif period_min and period_max:
                    period_str = f"{period_min}~{period_max}개월"
                elif period_min:
                    period_str = f"{period_min}개월 이상"
                elif period_max:
                    period_str = f"{period_max}개월 이하"
                else:
                    period_str = ""
                
                # 가입금액 포맷팅 개선
                amount_min = row[7] if row[7] and row[7] not in ['제한없음', '없음', ''] else None
                amount_max = row[8] if row[8] and row[8] not in ['제한없음', '없음', ''] else None
                
                if amount_min and amount_max and amount_min == amount_max:
                    amount_str = f"{amount_min}원"
                elif amount_min and amount_max:
                    amount_str = f"{amount_min}~{amount_max}원"
                elif amount_min:
                    amount_str = f"{amount_min}원 이상"
                elif amount_max:
                    amount_str = f"{amount_max}원 이하"
                else:
                    amount_str = ""
                
                # 설명 길이 제한
                description = row[9][:100] + "..." if row[9] and len(row[9]) > 100 else row[9]
                
                products.append({
                    "은행명": row[0],
                    "상품명": row[1],
                    "상품유형": row[2],
                    "기본금리": row[3],
                    "최대우대금리": row[4],
                    "계약기간": period_str,
                    "가입금액": amount_str,
                    "설명": description
                })

            return products

    except Exception as e:
        logger.error(f"[recommend_deposit_products] 실패: {e}", exc_info=True)
        # 임시 더미 데이터 반환 (전환용)
        return [
            {
                "은행명": "테스트은행",
                "상품명": "테스트 예금상품",
                "상품유형": "정기예금",
                "기본금리": 3.5,
                "최대우대금리": 4.0,
                "계약기간": "12개월",  # 수정됨
                "가입금액": "100만원 이상",  # 수정됨
                "설명": "기본 예금 상품으로 지정된 기간 동안 예금을 유지하면 우대 금리혜택을 받을 수 있습니다."
            },
            {
                "은행명": "개발은행",
                "상품명": "디버깅 적금",
                "상품유형": "정기적금",
                "기본금리": 4.2,
                "최대우대금리": 4.8,
                "계약기간": "24개월",  # 수정됨
                "가입금액": "10만원~50만원",  # 수정됨
                "설명": "매월 일정액을 저축하면서 고수익을 기대할 수 있는 적금 상품입니다."
            },
            {
                "은행명": "샘플은행",
                "상품명": "파이썬 저축예금",
                "상품유형": "자유입출금식",
                "기본금리": 2.8,
                "최대우대금리": 3.2,
                "계약기간": "없음",  # 수정됨
                "가입금액": "제한없음",  # 수정됨
                "설명": "자유롭게 입출금이 가능한 저축예금 상품입니다. 필요할 때 언제든지 사용할 수 있습니다."
            }
        ]

async def recommend_fund_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    펀드 상품 추천
    """

    try:
        logger.debug(f"[recommend_fund_products] 시작 - user_id: {user_id}, limit: {limit}")
        async with SessionMaker() as session:
            logger.debug("DB 세션 생성 성공")
            conditions = ["펀드성과정보_1년 IS NOT NULL", "펀드명 IS NOT NULL"]
            params = {"limit": limit}
            
            # 기본 위험 선호도 설정
            age = user_data.get("나이", 35)
            if age < 30:
                risk_pref = "주식형"
            elif age < 45:
                risk_pref = "혼합형"
            elif age < 60:
                risk_pref = "채권형"
            else:
                risk_pref = "안정형"

            # 감정, 재무상태로 조정
            dominant_emotion = emotion_data.get("dominant_emotion", "중립") if emotion_data else "중립"
            liquidity_score = user_data.get("유동성점수", 50.0)

            if (dominant_emotion in ["공포", "걱정", "슬픔"] or liquidity_score < 40) and risk_pref == "주식형":
                risk_pref = "혼합형"

            if risk_pref == "주식형":
                conditions.append("중유형 LIKE '%주식%'")
            elif risk_pref == "혼합형":
                conditions.append("(중유형 LIKE '%혼합%' OR 중유형 LIKE '%자산배분%')")
            elif risk_pref == "채권형":
                conditions.append("중유형 LIKE '%채권%'")
            else:
                conditions.append("(중유형 LIKE '%MMF%' OR 중유형 LIKE '%채권%')")

            where_clause = " AND ".join(conditions)

            query = text(f"""
                SELECT 
                    펀드명, 운용사명, 대유형, 중유형, 소유형,
                    펀드성과정보_1년, 펀드성과정보_6개월, 펀드성과정보_3개월,
                    투자위험등급, 투자전략, 순자산
                FROM 공모펀드상품
                WHERE {where_clause}
                ORDER BY 펀드성과정보_1년 DESC
                LIMIT :limit
            """).bindparams(**params)
            logger.debug(f"쿼리 생성: {query}")

            try:
                logger.debug("쿼리 실행 시작")
                result = await session.execute(query)
                rows = result.fetchall()
                logger.debug(f"쿼리 실행 성공, {len(rows)}개 결과 조회됨")
            except Exception as exe:
                logger.error(f"쿼리 실행 실패: {exe}")
                raise

            products = []
            for row in rows:
                # 수익률 포맷팅 (소수점 2자리로 제한)
                rate_1y = f"{row[5]:.2f}%" if row[5] else "0.00%"
                rate_6m = f"{row[6]:.2f}%" if row[6] else "0.00%"
                rate_3m = f"{row[7]:.2f}%" if row[7] else "0.00%"
                
                # 순자산 포맷팅
                asset_value = row[10]
                if asset_value:
                    if asset_value >= 1000000000000:  # 1조원 이상
                        asset_str = f"{asset_value/1000000000000:.2f}조원"
                    elif asset_value >= 100000000:  # 1억원 이상
                        asset_str = f"{asset_value/100000000:.2f}억원"
                    elif asset_value >= 10000:  # 1만원 이상
                        asset_str = f"{asset_value/10000:.2f}만원"
                    else:
                        asset_str = f"{asset_value:,}원"
                else:
                    asset_str = ""
                
                # 설명 길이 제한
                strategy = row[9][:100] + "..." if row[9] and len(row[9]) > 100 else row[9]
                
                # 유형 포맷팅 개선
                type_str = ""
                if row[2] and row[3] and row[4]:  # 대/중/소 유형 모두 있는 경우
                    type_str = f"{row[2]} > {row[3]} > {row[4]}"
                elif row[2] and row[3]:  # 대/중 유형만 있는 경우
                    type_str = f"{row[2]} > {row[3]}"
                elif row[2]:
                    type_str = row[2]
                
                products.append({
                    "펀드명": row[0],
                    "운용사": row[1],
                    "유형": type_str,
                    "1년수익률": rate_1y,
                    "6개월수익률": rate_6m,
                    "3개월수익률": rate_3m,
                    "위험등급": row[8],
                    "투자전략": strategy,
                    "순자산": asset_str
                })

            return products

    except Exception as e:
        logger.error(f"[recommend_fund_products] 실패: {e}", exc_info=True)
        # 임시 더미 데이터 반환 (전환용)
        return [
            {
                "펀드명": "테스트 주식형 펀드",
                "운용사": "테스트자산운용",
                "유형": "주식형 > 국내주식",
                "1년수익률": "8.50%",  # 수정됨
                "6개월수익률": "4.20%",  # 수정됨
                "3개월수익률": "2.10%",  # 수정됨
                "위험등급": "3등급(다소높은위험)",
                "투자전략": "국내 대형 우량주 중심 투자를 통한 자본이득 추구. 성장성 주식에 집중 투자하여 장기적 수익을 추구합니다.",
                "순자산": "500.00억원"  # 수정됨
            },
            {
                "펀드명": "안정성장 혼합형 펀드",
                "운용사": "샘플자산운용",
                "유형": "혼합형 > 채권혼합",
                "1년수익률": "5.80%",  # 수정됨
                "6개월수익률": "3.10%",  # 수정됨
                "3개월수익률": "1.50%",  # 수정됨
                "위험등급": "4등급(보통위험)",
                "투자전략": "채권 70%, 주식 30% 안정적 분산투자를 통한 균형 있는 자산 운용. 안정적인 채권 수익과 주식 투자를 통한 성장을 동시에 추구합니다.",
                "순자산": "350.00억원"  # 수정됨
            },
            {
                "펀드명": "채권형 안정 펀드",
                "운용사": "안전자산운용",
                "유형": "채권형 > 국내채권",
                "1년수익률": "3.20%",  # 수정됨
                "6개월수익률": "1.80%",  # 수정됨
                "3개월수익률": "0.90%",  # 수정됨
                "위험등급": "5등급(낮은위험)",
                "투자전략": "국내 우량 회사채 및 국채 중심 투자를 통한 안정적인 이자 수익 추구. 금리 변동에 따른 위험을 최소화하고 안정적인 수익을 제공합니다.",
                "순자산": "250.00억원"  # 수정됨
            }
        ]
