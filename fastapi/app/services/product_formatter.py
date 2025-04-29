import json
import logging
from typing import List, Dict, Any, Optional

# 로거 설정
logger = logging.getLogger(__name__)

# 상품 타입 정의
PRODUCT_TYPE_DEPOSIT = "deposit"
PRODUCT_TYPE_FUND = "fund"

def format_contract_period(period: Optional[str]) -> str:
    """계약기간 정리: 의미 없는 값은 제거, 단위 중복 수정"""
    if not period:
        return ""
    if any(k in period for k in ["제한없음", "무제한", "없음", "불명", "미정"]):
        return ""
    
    # '개월개월'과 같은 중복 단위 수정
    period = period.strip()
    if '개월개월' in period:
        period = period.replace('개월개월', '개월')
    return period

def format_join_amount(amount: Optional[str]) -> str:
    """가입금액 정리: 의미 없는 값은 제거, 단위 중복 수정"""
    if not amount or amount in ["0", "0원", "0~0", ""]:
        return ""
    
    # '원원'과 같은 중복 단위 수정
    amount = amount.strip()
    if '원원' in amount:
        amount = amount.replace('원원', '원')
    if '만원원' in amount:
        amount = amount.replace('만원원', '만원')
    return amount

def get_intro_message(emotion_data: Optional[Dict[str, Any]]) -> str:
    """감정에 따른 추천 인트로 메시지"""
    if not emotion_data:
        return "고객님께 맞는 상품을 추천해 드립니다."
    
    dominant_emotion = emotion_data.get("dominant_emotion", "중립")
    if dominant_emotion in ["화남", "슬픔"]:
        return "현재 상황이 어려우실 수 있지만, 다음 상품들이 도움이 될 수 있을 것 같습니다."
    elif dominant_emotion in ["공포"] or emotion_data.get("is_anxious", False):
        return "걱정이 많으신 것 같습니다. 안정적인 상품 위주로 추천해 드립니다."
    elif dominant_emotion == "행복":
        return "좋은 기분을 더 오래 유지할 수 있는 상품을 추천해 드립니다."
    else:
        return "고객님께 맞는 상품을 추천해 드립니다."

def format_single_deposit(product: Dict[str, Any]) -> str:
    """예금/적금 상품 하나 포맷"""
    logger.debug(f"format_single_deposit 호출: {json.dumps(product, ensure_ascii=False)}")
    lines = [
        f"**{product.get('상품명', '정보 없음')}** ({product.get('은행명', '정보 없음')})",
        f"- 상품유형: {product.get('상품유형', '정보 없음')}",
        f"- 기본금리: {product.get('기본금리', 0)}%" + (
            f" (최대 {product.get('최대우대금리')}%)" if product.get('최대우대금리') and product.get('최대우대금리') > product.get('기본금리', 0) else ""
        )
    ]

    contract_period = format_contract_period(product.get("계약기간", ""))
    if contract_period:
        # 추가 확인: 모든 단위 중복 방지
        if '개월' in contract_period and contract_period.count('개월') > 1:
            parts = contract_period.split('~')
            if len(parts) == 2:
                if '개월' in parts[0] and '개월' in parts[1]:
                    parts[0] = parts[0].replace('개월', '')
                    contract_period = f"{parts[0]}~{parts[1]}"
        lines.append(f"- 계약기간: {contract_period}")

    join_amount = format_join_amount(product.get("가입금액", ""))
    if join_amount:
        # 추가 확인: 모든 단위 중복 방지
        if '원' in join_amount and join_amount.count('원') > 1:
            parts = join_amount.split('~')
            if len(parts) == 2:
                if '원' in parts[0] and '원' in parts[1]:
                    parts[0] = parts[0].replace('원', '')
                    join_amount = f"{parts[0]}~{parts[1]}"
        lines.append(f"- 가입금액: {join_amount}")

    if product.get("설명"):
        lines.append(f"- 설명: {product['설명'][:100]}...")

    return "\n".join(lines)

def format_single_fund(product: Dict[str, Any]) -> str:
    """펀드 상품 하나 포맷"""
    lines = [
        f"**{product.get('펀드명', '정보 없음')}** ({product.get('운용사', '정보 없음')})",
        f"- 유형: {product.get('유형', '정보 없음')}",
        f"- 수익률: 1년 {product.get('1년수익률', 0)}%, 6개월 {product.get('6개월수익률', 0)}%, 3개월 {product.get('3개월수익률', 0)}%",
        f"- 위험등급: {product.get('위험등급', '정보 없음')}",
    ]

    if product.get("투자전략"):
        lines.append(f"- 투자전략: {product['투자전략'][:100]}...")

    return "\n".join(lines)

def format_product_recommendation(
    products: List[Dict[str, Any]],
    product_type: str,
    emotion_data: Optional[Dict[str, Any]] = None
) -> str:
    """추천 상품 전체 포맷팅"""
    
    logger.info(f"format_product_recommendation 호출됨: {len(products)}개 상품, 유형={product_type}")
    logger.debug(f"상품 데이터: {json.dumps(products, ensure_ascii=False)}")

    if not products:
        return "현재 추천할 수 있는 상품이 없습니다."

    intro_message = get_intro_message(emotion_data)

    if product_type == PRODUCT_TYPE_DEPOSIT:
        body = "\n\n".join(
            f"{i+1}. {format_single_deposit(p)}" for i, p in enumerate(products)
        )
        result = f"{intro_message}\n\n📌 **예금/적금 상품 추천**\n\n{body}\n\n해당 상품에 관심이 있으시면 더 자세한 정보를 알려드리겠습니다."
        logger.info(f"포맷팅된 결과 길이: {len(result)}")
        return result

    elif product_type == PRODUCT_TYPE_FUND:
        body = "\n\n".join(
            f"{i+1}. {format_single_fund(p)}" for i, p in enumerate(products)
        )
        result = f"{intro_message}\n\n📌 **펀드 상품 추천**\n\n{body}\n\n해당 상품에 관심이 있으시면 더 자세한 정보를 알려드리겠습니다."
        logger.info(f"포맷팅된 결과 길이: {len(result)}")
        return result

    else:
        return "지원하지 않는 상품 유형입니다."
