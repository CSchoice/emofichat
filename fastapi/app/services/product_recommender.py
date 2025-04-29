from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import aliased
from app.models.deposit import Bank, BankProduct
from app.models.fund import Fund, FundCompany, FundType, FundPerformance
from app.core.db import SessionMaker
import logging

# 로거 설정
logger = logging.getLogger(__name__)

PRODUCT_TYPE_DEPOSIT = "deposit"  # 예금/적금
PRODUCT_TYPE_FUND = "fund"         # 펀드

# 유틸리티 함수

async def recommend_deposit_products(
    user_id: str,
    user_data: Dict[str, Any],
    emotion_data: Dict[str, Any],
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    정규화된 bank_product 기반 예금/적금 추천
    """

    try:
        logger.debug(f"[recommend_deposit_products] 시작 - user_id: {user_id}, limit: {limit}")

        async with SessionMaker() as session:
            logger.debug("DB 세션 생성 성공")

            # 위험 선호도 가정 설정
            liquidity_score = user_data.get("유동성점수", 50.0)
            dominant_emotion = emotion_data.get("dominant_emotion", "중립") if emotion_data else "중립"

            # 기본 조건
            conditions = [
                BankProduct.base_interest_rate.isnot(None)
            ]

            # 감정/재무 상황 기반 추가 필터
            if (dominant_emotion in ["공포", "걱정", "슬픔"]) or liquidity_score < 30:
                # 초단기 상품 우선 추천
                conditions.append(BankProduct.min_period_days <= 90)  # 3개월 이하

            # 조인
            BankAlias = aliased(Bank)
            ProductAlias = aliased(BankProduct)

            select_query = select(
                BankAlias.bank_name,
                ProductAlias.product_name,
                ProductAlias.deposit_method,
                ProductAlias.base_interest_rate,
                ProductAlias.min_period_days,
                ProductAlias.max_period_days,
                ProductAlias.min_amount,
                ProductAlias.max_amount,
                ProductAlias.description
            ).join(
                BankAlias, BankAlias.bank_id == ProductAlias.bank_id
            ).where(
                *conditions
            ).order_by(
                ProductAlias.base_interest_rate.desc()
            ).limit(limit)

            logger.debug(f"쿼리 생성 완료: {select_query}")

            result = await session.execute(select_query)
            rows = result.fetchall()
            logger.debug(f"쿼리 실행 성공, {len(rows)}개 결과 조회됨")

            seen = set()
            products = []

            for row in rows:
                key = (row[0], row[1])  # 은행명 + 상품명 기준
                if key in seen:
                    continue
                seen.add(key)

                # 기간 포맷
                period_min = (row[4] // 30) if row[4] else None
                period_max = (row[5] // 30) if row[5] else None

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

                # 가입금액 포맷
                amount_min = row[6]
                amount_max = row[7]

                if amount_min and amount_max and amount_min == amount_max:
                    amount_str = f"{amount_min:,}원"
                elif amount_min and amount_max:
                    amount_str = f"{amount_min:,}~{amount_max:,}원"
                elif amount_min:
                    amount_str = f"{amount_min:,}원 이상"
                elif amount_max:
                    amount_str = f"{amount_max:,}원 이하"
                else:
                    amount_str = ""

                # 설명
                description = row[8][:100] + "..." if row[8] and len(row[8]) > 100 else row[8]

                products.append({
                    "은행명": row[0],
                    "상품명": row[1],
                    "상품유형": row[2],
                    "기본금리": row[3],
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

async def recommend_fund_products(user_id: str, user_data: Dict[str, Any], emotion_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """
    정규화된 펀드 테이블 기반 펀드 추천
    """
    try:
        logger.debug(f"[recommend_fund_products] 시작 - user_id: {user_id}, limit: {limit}")

        async with SessionMaker() as session:
            logger.debug("DB 세션 생성 성공")

            # 위험 성향 추론
            age = user_data.get("나이", 35)
            if age < 30:
                risk_pref = "주식형"
            elif age < 45:
                risk_pref = "혼합형"
            elif age < 60:
                risk_pref = "채권형"
            else:
                risk_pref = "안정형"

            dominant_emotion = emotion_data.get("dominant_emotion", "중립") if emotion_data else "중립"
            liquidity_score = user_data.get("유동성점수", 50.0)

            if (dominant_emotion in ["공포", "걱정", "슬픔"]) or liquidity_score < 40:
                if risk_pref == "주식형":
                    risk_pref = "혼합형"
                elif risk_pref == "혼합형":
                    risk_pref = "채권형"

            # 조건
            conditions = [FundPerformance.return_1y.isnot(None)]
            if risk_pref == "주식형":
                conditions.append(FundType.mid_category.like("%주식%"))
            elif risk_pref == "혼합형":
                conditions.append(FundType.mid_category.like("%혼합%"))
            elif risk_pref == "채권형":
                conditions.append(FundType.mid_category.like("%채권%"))
            else:
                conditions.append(FundType.mid_category.like("%MMF%"))

            # Aliased 객체
            F = aliased(Fund)
            FC = aliased(FundCompany)
            FT = aliased(FundType)
            FP = aliased(FundPerformance)

            query = select(
                        F.fund_name,
                        FC.company_name,
                        FT.large_category,
                        FT.mid_category,
                        FT.small_category,
                        FP.return_1y,
                        FP.return_6m,
                        FP.return_3m,
                        FP.sharpe_ratio_1y,
                        F.setup_date
                    ).join(
                        FC, F.company_id == FC.company_id
                    ).join(
                        FT, F.type_id == FT.type_id
                    ).join(
                        FP, F.fund_id == FP.fund_id
                    ).where(
                        FP.return_1y.isnot(None),
                        FT.mid_category.like("%주식%")
                    ).order_by(
                        FP.return_1y.desc()
                    ).limit(3)

            result = await session.execute(query)
            rows = result.fetchall()

            products = []
            seen = set()
            for row in rows:
                # 중복 체크 기준: (운용사명, 대유형, 1년수익률)
                key = (row[1], row[2], row[5])  # (운용사명, 대유형, 1년수익률)
                if key in seen:
                    continue
                seen.add(key)

                products.append({
                    "펀드명": row[0],
                    "운용사": row[1],
                    "유형": " > ".join(filter(None, [row[2], row[3], row[4]])),
                    "1년수익률": f"{row[5]:.2f}%" if row[5] else "0.00%",
                    "6개월수익률": f"{row[6]:.2f}%" if row[6] else "0.00%",
                    "3개월수익률": f"{row[7]:.2f}%" if row[7] else "0.00%",
                    "Sharpe Ratio": f"{row[8]:.2f}" if row[8] else "N/A",
                    "설정일": row[9].strftime("%Y-%m-%d") if row[9] else "정보 없음"
                })

                if len(products) >= limit:
                    break

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
