from __future__ import annotations


def calculate_data_confidence(useful_review_count: int) -> str:
    """
    Server policy (single source of truth):
    - <5: insufficient
    - 5~9: low
    - 10~19: medium
    - >=20: high
    """
    try:
        n = int(useful_review_count)
    except Exception:
        n = 0

    if n < 5:
        return "insufficient"
    if n < 10:
        return "low"
    if n < 20:
        return "medium"
    return "high"


def confidence_reason(data_confidence: str) -> str:
    dc = (data_confidence or "").strip()
    if dc == "insufficient":
        return "실질 리뷰가 5개 미만이라 신뢰도 있는 고급 분석이 어렵습니다."
    if dc == "low":
        return "실질 리뷰가 5~9개로 적어 제한적인 분석입니다."
    if dc == "medium":
        return "실질 리뷰 10개 이상을 기준으로 분석했습니다."
    if dc == "high":
        return "실질 리뷰 20개 이상을 기준으로 비교적 안정적으로 분석했습니다."
    return ""


def should_save_map_flag(status: str, data_confidence: str, real_score: float) -> bool:
    """
    map_flag 저장 가능 조건:
    - status == "ok"
    - dataConfidence in ("medium", "high")
    - realScore >= 3.5
    """
    if (status or "") != "ok":
        return False
    if (data_confidence or "") not in ("medium", "high"):
        return False
    try:
        s = float(real_score)
    except Exception:
        return False
    return s >= 3.5

