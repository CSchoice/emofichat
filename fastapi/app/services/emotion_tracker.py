"""
감정 변화 추적 서비스

사용자의 시간별 감정 변화를 추적하고 장기적인 금융 건강을 모니터링합니다.
"""

from typing import Dict, List, Any
import logging
import json
from datetime import datetime, timedelta
import statistics
from collections import Counter

from app.core.redis_client import get_redis
from app.services.emotion_analyzer import get_emotion_analyzer

logger = logging.getLogger(__name__)

# 감정 가중치 정의 (금융 스트레스 관점)
EMOTION_WEIGHTS = {
    "슬픔": 0.7,
    "중립": 0.0,
    "화남": 0.8,
    "걱정": 0.9,
    "행복": -0.5,
    # 추가 감정 가중치
    "혐오": 0.8,  # 부정적
    "공포": 0.9,  # 매우 부정적
    "놀람": 0.2,  # 중립적
}

# 감정 히스토리 키 접두사
EMOTION_HISTORY_KEY_PREFIX = "emotion_hist:"

async def record_emotion(user_id: str, emotion_data: Dict[str, Any]) -> bool:
    """
    사용자의 감정 데이터를 기록합니다.
    최근 100개까지 Redis 리스트에 저장하며, JSON 직렬화를 사용합니다.
    """
    try:
        redis = await get_redis()
        # dominant 감정 추출 및 LABEL 매핑
        dominant = emotion_data.get("dominant_emotion", "중립")
        if isinstance(dominant, str) and dominant.startswith("LABEL_"):
            analyzer = await get_emotion_analyzer()
            dominant = analyzer.label_mapping.get(dominant, dominant)
        # 기록 객체 생성
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "dominant_emotion": dominant,
            "dominant_score": emotion_data.get("dominant_score", 0.0),
            "is_negative": emotion_data.get("is_negative", False),
            "is_anxious": emotion_data.get("is_anxious", False),
            "all_emotions": emotion_data.get("all_emotions", {}),
        }
        key = f"{EMOTION_HISTORY_KEY_PREFIX}{user_id}"
        # Redis 파이프라인으로 LPUSH & LTRIM
        pipe = redis.pipeline()
        pipe.lpush(key, json.dumps(record))
        pipe.ltrim(key, 0, 99)
        await pipe.execute()
        return True
    except Exception as e:
        logger.error(f"감정 기록 저장 오류: {e}")
        return False

async def get_emotion_history(user_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """
    사용자 감정 히스토리를 JSON 파싱하여 반환합니다.
    """
    try:
        redis = await get_redis()
        key = f"{EMOTION_HISTORY_KEY_PREFIX}{user_id}"
        entries = await redis.lrange(key, 0, -1)
        history: List[Dict[str, Any]] = []
        for item in entries:
            try:
                history.append(json.loads(item))
            except json.JSONDecodeError:
                continue
        if days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            history = [rec for rec in history if datetime.fromisoformat(rec["timestamp"]) >= cutoff]
        return history
    except Exception as e:
        logger.error(f"감정 히스토리 조회 오류: {e}")
        return []

async def analyze_emotion_trends(user_id: str, days: int = 30) -> Dict[str, Any]:
    """
    사용자 감정 트렌드 분석.
    """
    history = await get_emotion_history(user_id, days)
    if not history:
        return {"status": "no_data", "message": "데이터가 충분하지 않습니다."}
    # 빈도 계산
    doms = [r["dominant_emotion"] for r in history]
    freq = Counter(doms)
    most_common = freq.most_common(1)[0][0]

    # 평균 점수 계산
    avg_scores: Dict[str, float] = {}
    for emo in history[0].get("all_emotions", {}):
        scores = [r["all_emotions"].get(emo, 0) for r in history]
        if scores:
            avg_scores[emo] = sum(scores) / len(scores)

    # 부정/불안 비율
    neg_ratio = sum(r.get("is_negative", False) for r in history) / len(history)
    anx_ratio = sum(r.get("is_anxious", False) for r in history) / len(history)

    # 금융 스트레스 지수 계산 (가중치 처리)
    weighted: List[float] = []
    for r in history:
        dom = r.get("dominant_emotion", "중립")
        # 복합 감정 처리
        if ";" in dom:
            parts = dom.split(";")
            w = sum(EMOTION_WEIGHTS.get(p, 0) for p in parts) / len(parts)
        else:
            w = EMOTION_WEIGHTS.get(dom, 0)
        weighted.append(r.get("dominant_score", 0) * w)

    volatility = statistics.stdev(weighted) if len(weighted) > 1 else 0
    stress_idx = (sum(weighted) / len(weighted) + 1) * 50 if weighted else 50
    stress_idx = max(0, min(100, stress_idx))

    # 트렌드 감지
    trend = "변화없음"
    if len(weighted) >= 10:
        recent_avg = sum(weighted[:5]) / 5
        older_avg = sum(weighted[5:10]) / 5
        if recent_avg - older_avg > 0.2:
            trend = "스트레스증가"
        elif older_avg - recent_avg > 0.2:
            trend = "스트레스감소"

    recs = generate_recommendations(freq, stress_idx, trend)
    return {
        "status": "success",
        "most_frequent_emotion": most_common,
        "emotion_frequency": dict(freq),
        "avg_emotion_scores": avg_scores,
        "negative_ratio": neg_ratio,
        "anxious_ratio": anx_ratio,
        "emotion_volatility": volatility,
        "financial_stress_index": stress_idx,
        "stress_trend": trend,
        "data_points": len(history),
        "recommendations": recs,
    }


def generate_recommendations(emotion_frequency: Dict[str, int], stress_index: float, trend: str) -> List[str]:
    recs: List[str] = []
    dom = max(emotion_frequency, key=emotion_frequency.get)
    if stress_index > 75:
        recs.append("금융 스트레스가 매우 높습니다. 전문가 상담을 고려하세요.")
        if dom == "걱정":
            recs.append("장기 플랜 수립으로 불안 줄이기")
        elif dom == "화남":
            recs.append("충동 결제 자제하고 계획 세우기")
    elif stress_index > 50:
        recs.append("금융 스트레스가 높습니다. 지출 패턴 점검하기")
        if trend == "스트레스증가":
            recs.append("최근 스트레스 증가, 지출 우선순위 재조정")
    else:
        recs.append("현재 금융 스트레스가 낮습니다. 현재 습관 유지하세요.")
        if dom == "행복":
            recs.append("장기 저축 및 투자 고려하기")
    if trend == "스트레스증가":
        recs.append("지출 재검토하여 스트레스 완화")
    elif trend == "스트레스감소":
        recs.append("현재 전략 효과적입니다.")
    return recs

async def get_financial_health_summary(user_id: str) -> Dict[str, Any]:
    trends = await analyze_emotion_trends(user_id)
    return {
        "user_id": user_id,
        "emotion_analysis": trends,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": f"금융 스트레스 지수: {trends.get('financial_stress_index', 0):.1f}/100",
        "recommendations": trends.get('recommendations', []),
    }
