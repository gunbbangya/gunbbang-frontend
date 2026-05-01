from __future__ import annotations


def sanitize_ai_result(data: dict, mode: str) -> dict:
    """
    OpenAI JSON 응답을 검증·정규화. mode: fast(스니펫)·deep(카카오 심층).
    - Server-calculated metadata는 최종 저장 시 서버 값으로 덮어쓴다.
      여기서는 타입/기본값만 보정한다.
    """
    if not isinstance(data, dict):
        data = {}
    out = dict(data)

    def _str_safe(x) -> str:
        return "" if x is None else str(x)

    try:
        rs = float(out.get("realScore", 2.5))
    except (TypeError, ValueError):
        rs = 2.5
    out["realScore"] = max(1.0, min(5.0, rs))

    try:
        ep = int(round(float(out.get("eventProbability", 0))))
    except (TypeError, ValueError):
        ep = 0
    out["eventProbability"] = max(0, min(100, ep))

    raw_details = out.get("details")
    if not isinstance(raw_details, dict):
        raw_details = {}

    def _axis(key: str, default: float) -> float:
        try:
            v = float(raw_details.get(key, default))
        except (TypeError, ValueError):
            v = default
        return max(1.0, min(5.0, v))

    out["details"] = {
        "taste": _axis("taste", 2.75),
        "value": _axis("value", 2.75),
        "service": _axis("service", 3.0),
        "time": _axis("time", 3.0),
        "hygiene": _axis("hygiene", 3.0),
    }

    tag_keys = ("mustTryMenus", "vibeTags", "riskFlags")
    if mode == "deep":
        for k in tag_keys:
            v = out.get(k)
            if not isinstance(v, list):
                v = []
            cleaned: list[str] = []
            for it in v:
                if it is None:
                    continue
                if isinstance(it, str):
                    s = it.strip()
                    if s:
                        cleaned.append(s)
                    continue
                try:
                    s = str(it).strip()
                except Exception:
                    s = ""
                if s:
                    cleaned.append(s)
            out[k] = cleaned
    else:
        for k in tag_keys:
            if k in out and not isinstance(out[k], list):
                out[k] = []

    out["aiSummary"] = _str_safe(out.get("aiSummary"))
    if mode == "deep":
        out["romanizedName"] = _str_safe(out.get("romanizedName"))
    elif "romanizedName" in out:
        out["romanizedName"] = _str_safe(out.get("romanizedName"))

    # --- Deep pipeline metadata (server will overwrite final values) ---
    dc = _str_safe(out.get("dataConfidence")).strip()
    if dc not in ("insufficient", "low", "medium", "high"):
        dc = ""
    out["dataConfidence"] = dc
    out["confidenceReason"] = _str_safe(out.get("confidenceReason")).strip()

    for k in ("sourceStats", "reviewPatternStats", "reviewerSignals"):
        v = out.get(k)
        out[k] = v if isinstance(v, dict) else {}

    nm = "리뷰상 확인 불가(Not mentioned)"
    pi = out.get("practicalInfo")
    if not isinstance(pi, dict):
        pi = {}
    for key in ("parking", "waiting", "bestTime", "foreignerAccess"):
        v = pi.get(key)
        s = _str_safe(v).strip()
        pi[key] = s if s else nm
    out["practicalInfo"] = pi

    return out

