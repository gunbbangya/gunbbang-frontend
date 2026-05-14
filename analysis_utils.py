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

    tag_keys = ("mustTryMenus", "vibeTags")
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
        for k in tag_keys + ("riskFlags",):
            if k in out and not isinstance(out[k], list):
                out[k] = []

    nm_fast = "리뷰상 확인 불가(Not mentioned)"
    nm_deep = "Not mentioned in reviews."

    if mode == "deep":
        allowed_rf_types = {
            "waiting",
            "service",
            "hygiene",
            "price",
            "taste",
            "ordering",
            "crowding",
            "tourist_trap",
            "data_limit",
        }
        allowed_levels = {"high", "medium", "low"}
        rf_in = out.get("riskFlags")
        rf_out: list[dict] = []
        if isinstance(rf_in, list):
            for it in rf_in:
                if isinstance(it, dict):
                    t = _str_safe(it.get("type")).strip().lower()
                    if t not in allowed_rf_types:
                        t = "data_limit"
                    lv = _str_safe(it.get("level")).strip().lower()
                    if lv not in allowed_levels:
                        lv = "low"
                    rsn = _str_safe(it.get("reason")).strip() or nm_deep
                    rf_out.append({"type": t, "level": lv, "reason": rsn})
                elif it is not None and _str_safe(it).strip():
                    rf_out.append(
                        {"type": "data_limit", "level": "low", "reason": _str_safe(it).strip()}
                    )
        out["riskFlags"] = rf_out

        dec_raw = out.get("decision")
        if not isinstance(dec_raw, dict):
            dec_raw = {}
        lbl = _str_safe(dec_raw.get("label")).strip().upper().replace(" ", "_")
        allowed_lbl = {"GO", "OK", "CAUTION", "AVOID", "INSUFFICIENT_DATA"}
        if lbl not in allowed_lbl:
            lbl = "CAUTION"
        vss_raw = dec_raw.get("visitSafetyScore")
        vss: float | None
        if vss_raw is None and lbl == "INSUFFICIENT_DATA":
            vss = None
        else:
            try:
                vss = float(vss_raw if vss_raw is not None else out.get("realScore", 2.5))
            except (TypeError, ValueError):
                vss = float(out.get("realScore", 2.5))
            vss = max(1.0, min(5.0, vss))
        out["decision"] = {
            "label": lbl,
            "visitSafetyScore": vss,
            "oneLine": _str_safe(dec_raw.get("oneLine")).strip() or nm_deep,
            "shortReason": _str_safe(dec_raw.get("shortReason")).strip() or nm_deep,
        }
        if vss is not None:
            out["realScore"] = vss
        else:
            try:
                rs_keep = float(out.get("realScore", 2.5))
            except (TypeError, ValueError):
                rs_keep = 2.5
            out["realScore"] = max(1.0, min(5.0, rs_keep))

        def _str_list(key: str, *, cap: int = 12) -> list[str]:
            v = out.get(key)
            if not isinstance(v, list):
                return []
            o: list[str] = []
            for it in v:
                s = _str_safe(it).strip()
                if s and s not in o:
                    o.append(s)
                if len(o) >= cap:
                    break
            return o

        out["whoShouldGo"] = _str_list("whoShouldGo", cap=10)
        out["whoShouldAvoid"] = _str_list("whoShouldAvoid", cap=10)

        mk: list[dict] = []
        mk_in = out.get("mustKnowBeforeGoing")
        if isinstance(mk_in, list):
            for it in mk_in:
                if not isinstance(it, dict):
                    continue
                imp = _str_safe(it.get("importance")).strip().lower()
                if imp not in ("high", "medium", "low"):
                    imp = "medium"
                mk.append(
                    {
                        "point": _str_safe(it.get("point")).strip() or nm_deep,
                        "evidence": _str_safe(it.get("evidence")).strip() or nm_deep,
                        "importance": imp,
                    }
                )
        out["mustKnowBeforeGoing"] = mk[:12]

        pi = out.get("practicalInfo")
        if not isinstance(pi, dict):
            pi = {}
        pi_keys = (
            "waiting",
            "parking",
            "soloFriendly",
            "groupFriendly",
            "dateFriendly",
            "foreignerAccess",
            "orderingDifficulty",
            "englishMenu",
            "bestTimeToVisit",
        )
        pi_out: dict[str, str] = {}
        for pk in pi_keys:
            v = pi.get(pk)
            if pk == "bestTimeToVisit":
                v = v or pi.get("bestTime")
            s = _str_safe(v).strip()
            pi_out[pk] = s if s else nm_deep
        out["practicalInfo"] = pi_out

        fs = out.get("foodSignals")
        if not isinstance(fs, dict):
            fs = {}
        menus = fs.get("mentionedMenus")
        mm: list[str] = []
        if isinstance(menus, list):
            for it in menus:
                s = _str_safe(it).strip()
                if s and s not in mm:
                    mm.append(s)
                if len(mm) >= 16:
                    break
        if not mm and isinstance(out.get("mustTryMenus"), list):
            mm = [str(x).strip() for x in out["mustTryMenus"] if str(x).strip()][:8]
        out["foodSignals"] = {
            "mentionedMenus": mm,
            "tastePattern": _str_safe(fs.get("tastePattern")).strip() or nm_deep,
            "portionValuePattern": _str_safe(fs.get("portionValuePattern")).strip() or nm_deep,
        }

        ar = out.get("alternativeRecommendation")
        if not isinstance(ar, dict):
            ar = {}
        aq = ar.get("alternativeQuery")
        if not isinstance(aq, dict):
            aq = {}
        try:
            max_dm = int(aq.get("maxDistanceMeters") if aq.get("maxDistanceMeters") is not None else 800)
        except (TypeError, ValueError):
            max_dm = 800
        max_dm = max(100, min(5000, max_dm))
        pref = aq.get("preferredLowerRisks")
        pref_list: list[str] = []
        if isinstance(pref, list):
            for p in pref:
                s = _str_safe(p).strip().lower()
                if s and s in allowed_rf_types and s not in pref_list:
                    pref_list.append(s)
        out["alternativeRecommendation"] = {
            "shouldRecommend": bool(ar.get("shouldRecommend")),
            "reason": _str_safe(ar.get("reason")).strip() or nm_deep,
            "alternativeQuery": {
                "sameArea": bool(aq.get("sameArea", True)),
                "sameCategory": bool(aq.get("sameCategory", True)),
                "maxDistanceMeters": max_dm,
                "preferredLowerRisks": pref_list[:8]
                or ["waiting", "hygiene", "service"],
            },
        }

        conf = out.get("confidence")
        if not isinstance(conf, dict):
            conf = {}
        cl = _str_safe(conf.get("level")).strip().lower()
        if cl not in ("high", "medium", "low"):
            cl = ""
        dl = conf.get("dataLimitations")
        dl_out: list[str] = []
        if isinstance(dl, list):
            for it in dl:
                s = _str_safe(it).strip()
                if s:
                    dl_out.append(s)
        try:
            urc = int(conf.get("usedReviewCount") if conf.get("usedReviewCount") is not None else 0)
        except (TypeError, ValueError):
            urc = 0
        out["confidence"] = {
            "level": cl,
            "reason": _str_safe(conf.get("reason")).strip() or nm_deep,
            "usedReviewCount": max(0, urc),
            "dataLimitations": dl_out[:12],
        }

        one = out["decision"]["oneLine"]
        three = out["decision"]["shortReason"]
        out["aiSummary"] = f"[Decision] {one}\n[Why] {three}".strip()
    else:
        v = out.get("riskFlags")
        if not isinstance(v, list):
            v = []
        cleaned_rf: list[str] = []
        for it in v:
            if it is None:
                continue
            if isinstance(it, str):
                s = it.strip()
                if s:
                    cleaned_rf.append(s)
                continue
            if isinstance(it, dict):
                s = _str_safe(it.get("reason") or it.get("type")).strip()
                if s:
                    cleaned_rf.append(s)
                continue
            try:
                s = str(it).strip()
            except Exception:
                s = ""
            if s:
                cleaned_rf.append(s)
        out["riskFlags"] = cleaned_rf

    out["aiSummary"] = _str_safe(out.get("aiSummary"))
    if mode == "deep":
        out["romanizedName"] = _str_safe(out.get("romanizedName"))
    elif "romanizedName" in out:
        out["romanizedName"] = _str_safe(out.get("romanizedName"))

    dc_raw = out.get("dataConfidence")
    dc = _str_safe(dc_raw).strip()
    if dc not in ("insufficient", "low", "medium", "high"):
        dc = ""
    out["dataConfidence"] = dc

    out["confidenceReason"] = _str_safe(out.get("confidenceReason")).strip()

    if mode == "fast":
        sm = _str_safe(out.get("scoreMeaning")).strip()
        if sm != "review_risk_screening":
            out["scoreMeaning"] = "review_risk_screening"

    for k in ("sourceStats", "reviewPatternStats", "reviewerSignals"):
        v = out.get(k)
        out[k] = v if isinstance(v, dict) else {}

    if mode != "deep":
        pi = out.get("practicalInfo")
        if not isinstance(pi, dict):
            pi = {}
        for key in ("parking", "waiting", "bestTime", "foreignerAccess"):
            v = pi.get(key)
            s = _str_safe(v).strip()
            pi[key] = s if s else nm_fast
        out["practicalInfo"] = pi

    return out
