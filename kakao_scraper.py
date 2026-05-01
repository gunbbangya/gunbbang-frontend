import os
import re
import time
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

_DISCARD_ADDR_TOKENS = frozenset(
    {
        "대한민국",
        "한국",
        "KR",
        "Korea",
        "South",
    }
)


def _addr_tokens(addr: str) -> set[str]:
    if not addr or not str(addr).strip():
        return set()
    s = re.sub(r"[\s,]+", " ", str(addr).strip())
    return {w for w in s.split() if w and w not in _DISCARD_ADDR_TOKENS and len(w) > 0}


def _name_match_bonus(name_query: str, place_name: str) -> int:
    """쿼리와 카카오 상호(지번/도로) 유사 보너스."""
    if not name_query or not place_name:
        return 0
    nq = re.sub(r"\s+", "", name_query)
    pn = re.sub(r"\s+", "", place_name)
    if not nq or not pn:
        return 0
    if nq in pn or pn in nq:
        return 2
    return 0


def _doc_rank_key(google_address: str, doc: dict, name_query: str) -> tuple:
    """(주소 토큰 겹침, 상호·쿼리 보나스) — 앞이 더 큰 후보를 우선."""
    g = _addr_tokens(google_address)
    if not g:
        return (0, _name_match_bonus(name_query, doc.get("place_name", "") or ""))
    k_all = _addr_tokens(doc.get("address_name", "")) | _addr_tokens(
        doc.get("road_address_name", "")
    )
    ov = len(g & k_all)
    nb = _name_match_bonus(name_query, doc.get("place_name", "") or "")
    return (ov, nb)


# overlap + name_bonus 합이 이 값 미만이면 매칭 거부 (억지 1순위 방지)
_MIN_COMBINED_MATCH_SCORE = 1


def get_kakao_place_id(
    place_name: str, google_address: str,
) -> dict | None:
    """
    키워드 검색 후, 구글 주소와 토큰·상호로 최적 후보를 고른다.
    overlap + name_bonus 합(score)가 기준 미만이면 매칭 실패(None).

    성공 시:
        {\"place_id\": str, \"matched_name\": str, \"matched_address\": str}
    """
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(
            url, headers=headers, params={"query": place_name, "size": 15}
        )
        if res.status_code != 200 or not res.json().get("documents"):
            return None

        docs = res.json()["documents"]

        ga = str(google_address or "").strip()
        google_has_anchor = bool(_addr_tokens(google_address))

        best_doc = max(docs, key=lambda d: _doc_rank_key(google_address, d, place_name))
        rk = _doc_rank_key(google_address, best_doc, place_name)
        overlap, name_bonus = rk[0], rk[1]
        score = overlap + name_bonus

        a1 = (best_doc.get("address_name") or "").strip()
        a2 = (best_doc.get("road_address_name") or "").strip()
        pname = (best_doc.get("place_name") or "").strip()

        print(
            f"🎯 [카카오 주소교차] 쿼리='{place_name[:60]}' → "
            f"후보(겹침 {overlap}·상호보너스 {name_bonus}·합산 {score}) {pname} / {a1 or a2}"
        )

        # 구글 주소가 있어도 토큰이 비면, 이름 보너스만으로는 첫 줄 강매 방지 가능
        if ga and google_has_anchor and score <= 0:
            print(
                f"   🚫 [카카오] 매칭 거부: 합산 점수 {score} ≤ 0 (주소 앵커 있음)"
            )
            return None
        if ga and google_has_anchor and score < _MIN_COMBINED_MATCH_SCORE:
            print(
                f"   🚫 [카카오] 매칭 거부: 합산 점수 {score} < {_MIN_COMBINED_MATCH_SCORE}"
            )
            return None

        # 주소 문자열 없음: 상호 문자열 포함(보너스≥2)일 때만 1건 채택; 아니면 실패
        if not ga or not google_has_anchor:
            if name_bonus < 2:
                print(
                    "   🚫 [카카오] 매칭 거부: 구글 주소 앵커 없고 상호 문자열 포함 관계 없음"
                )
                return None
            if score < _MIN_COMBINED_MATCH_SCORE:
                print(
                    f"   🚫 [카카오] 매칭 거부: 합산 점수 {score} < {_MIN_COMBINED_MATCH_SCORE}"
                )
                return None

        if len(docs) > 1 and overlap == 0 and google_has_anchor:
            print(
                "   ⚠️ [카카오] 주소 토큰 겹침 0 — 상호 보너스로만 후보 확정(위에서 점수 통과)"
            )

        return {
            "place_id": best_doc["id"],
            "matched_name": pname,
            # address_name(지번) 또는 road_address_name(도로명) 중 존재하는 값
            "matched_address": a1 or a2,
        }

    except Exception as e:
        print(f"🚨 카카오 ID 검색 실패: {e}")
    return None


def _normalize_review_text(text: str) -> str:
    """중복 제거용 normalize (의미 보존 목적, 과한 가공 금지)."""
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _safe_int(x):
    try:
        return int(x)
    except Exception:
        return None


def _compute_reviewer_signals(reviews: list[dict]) -> dict:
    collected = len(reviews) if reviews else 0
    if collected <= 0:
        return {
            "visibleReviewerCount": 0,
            "reviewerMetaCoverageRatio": 0.0,
            "lowActivityReviewerRatio": None,
            "experiencedReviewerRatio": None,
            "balancedRatingReviewerRatio": None,
            "mostlyPositiveReviewerRatio": None,
            "harshReviewerRatio": None,
        }

    visible = 0
    rc_vals: list[int] = []
    avg_vals: list[float] = []

    for r in reviews:
        if not isinstance(r, dict):
            continue
        rc = r.get("reviewerReviewCount")
        ar = r.get("reviewerAverageRating")
        if rc is not None or ar is not None:
            visible += 1
        if isinstance(rc, int):
            rc_vals.append(rc)
        if isinstance(ar, (int, float)):
            avg_vals.append(float(ar))

    coverage = (visible / collected) if collected else 0.0

    def _ratio_int(pred) -> float | None:
        if not rc_vals:
            return None
        hit = sum(1 for v in rc_vals if pred(v))
        return hit / len(rc_vals)

    def _ratio_float(pred) -> float | None:
        if not avg_vals:
            return None
        hit = sum(1 for v in avg_vals if pred(v))
        return hit / len(avg_vals)

    return {
        "visibleReviewerCount": visible,
        "reviewerMetaCoverageRatio": round(float(coverage), 4),
        "lowActivityReviewerRatio": None if not rc_vals else round(float(_ratio_int(lambda v: 1 <= v <= 3) or 0.0), 4),
        "experiencedReviewerRatio": None if not rc_vals else round(float(_ratio_int(lambda v: v >= 30) or 0.0), 4),
        "balancedRatingReviewerRatio": None
        if not avg_vals
        else round(float(_ratio_float(lambda v: 3.0 <= v <= 4.2) or 0.0), 4),
        "mostlyPositiveReviewerRatio": None
        if not avg_vals
        else round(float(_ratio_float(lambda v: v >= 4.7) or 0.0), 4),
        "harshReviewerRatio": None
        if not avg_vals
        else round(float(_ratio_float(lambda v: v <= 2.5) or 0.0), 4),
    }


def _scroll_plan(max_reviews: int) -> tuple[int, int]:
    """
    (scroll_times, hard_cap)
    - 무한 루프 방지용 상한을 제공한다.
    """
    mr = max(1, int(max_reviews or 25))
    if mr <= 25:
        return (4, 120)
    if mr <= 50:
        return (7, 220)
    return (12, 400)


def _parse_review_fields(raw: str) -> dict:
    """
    li.innerText 기반 느슨한 파서.
    - 안정적으로 확인 가능한 값만 채우고, 불확실하면 None 유지.
    - 닉네임/프로필/식별자는 추출하지 않는다.
    """
    s = (raw or "").strip()
    s_compact = re.sub(r"\s+", " ", s)

    # 날짜: YYYY.MM.DD
    date = None
    m_date = re.search(r"\b(\d{4}\.\d{2}\.\d{2})\.\b|\b(\d{4}\.\d{2}\.\d{2})\b", s_compact)
    if m_date:
        date = (m_date.group(1) or m_date.group(2) or "").strip() or None

    # 리뷰 별점(리뷰별) — 표기될 때만
    rating = None
    m_rating = re.search(r"(?:별점|평점)\s*([0-9]+(?:\.[0-9]+)?)", s_compact)
    if m_rating:
        rating = _safe_float(m_rating.group(1))

    reviewer_review_count = None
    m_rc = re.search(r"리뷰\s*([0-9,]+)\s*개", s_compact)
    if m_rc:
        reviewer_review_count = _safe_int(m_rc.group(1).replace(",", ""))

    reviewer_avg_rating = None
    m_ar = re.search(r"평균\s*([0-9]+(?:\.[0-9]+)?)", s_compact)
    if m_ar:
        reviewer_avg_rating = _safe_float(m_ar.group(1))

    # 본문: 줄 단위로 합치되, 날짜/도움돼요 등 UI 조각이 섞일 수 있으므로 최소한의 정리만
    text = " ".join([ln.strip() for ln in (raw or "").split("\n") if ln and ln.strip()])
    text = _normalize_review_text(text)

    return {
        "text": text,
        "date": date,
        "rating": rating,
        "reviewerReviewCount": reviewer_review_count,
        "reviewerAverageRating": reviewer_avg_rating,
    }


def get_deep_kakao_reviews(place_id: str, max_reviews: int = 25) -> dict:
    """
    카카오 place 페이지에서 리뷰를 수집한다.

    개인정보/식별자(닉네임/프로필 URL 등)는 수집·저장하지 않는다.
    가능하면 공개 숫자 시그널(작성자 리뷰 개수, 작성자 평균 평점, 도움돼요 수, 리뷰 별점)을 함께 추출한다.
    """
    mr = 25
    try:
        mr = int(max_reviews)
    except Exception:
        mr = 25
    if mr <= 0:
        mr = 25

    reviews_out: list[dict] = []
    place_url = f"https://place.map.kakao.com/{place_id}"
    kakao_total_review_count = None
    kakao_average_rating = None
    fallback_used = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        review_direct_url = f"{place_url}#review"
        print(f"🕵️‍♂️ [카카오 크롤러] 출동: {review_direct_url}")

        try:
            page.goto(review_direct_url)
            time.sleep(3)

            scroll_times, hard_cap = _scroll_plan(mr)
            for _ in range(scroll_times):
                page.mouse.wheel(0, 1000)
                time.sleep(0.9)
                # 펼치기(더보기)는 가끔만 시도
                try:
                    more_buttons = page.get_by_text("더보기", exact=True)
                    # 너무 많이 클릭하면 느려질 수 있으므로 상한
                    for i in range(min(10, more_buttons.count())):
                        more_buttons.nth(i).click(timeout=700)
                        time.sleep(0.25)
                except Exception:
                    pass

            extracted = page.evaluate(
                r"""(hardCap) => {
                const safeNum = (s) => {
                  if (!s) return null;
                  const m = String(s).replace(/,/g, "").match(/(\d+(\.\d+)?)/);
                  if (!m) return null;
                  const v = Number(m[1]);
                  return Number.isFinite(v) ? v : null;
                };

                const bodyText = (document.body && document.body.innerText) ? document.body.innerText : "";
                const totalCandidates = [
                  bodyText.match(/리뷰\s*([0-9,]+)\s*개/),
                  bodyText.match(/후기\s*([0-9,]+)\s*개/),
                ].filter(Boolean);
                const avgCandidates = [
                  bodyText.match(/평점\s*([0-9]+(\.[0-9]+)?)/),
                  bodyText.match(/별점\s*([0-9]+(\.[0-9]+)?)/),
                ].filter(Boolean);
                const total = totalCandidates.length ? Number(String(totalCandidates[0][1]).replace(/,/g,"")) : null;
                const avg = avgCandidates.length ? Number(avgCandidates[0][1]) : null;

                const lis = Array.from(document.querySelectorAll("li")).slice(0, hardCap);
                const reviewLis = lis.filter(li => /\d{4}\.\d{2}\.\d{2}\./.test(li.innerText || ""));
                const rawItems = reviewLis.map(li => (li.innerText || "").trim()).filter(Boolean);

                return {
                  meta: {
                    kakao_total_review_count: Number.isFinite(total) ? total : null,
                    kakao_average_rating: Number.isFinite(avg) ? avg : null,
                  },
                  rawItems,
                };
              }""",
                hard_cap,
            )

            raw_items = []
            if extracted and isinstance(extracted, dict):
                meta = extracted.get("meta") or {}
                if isinstance(meta, dict):
                    kakao_total_review_count = meta.get("kakao_total_review_count")
                    kakao_average_rating = meta.get("kakao_average_rating")
                raw_items = extracted.get("rawItems") or []

            if isinstance(raw_items, list) and raw_items:
                seen: set[str] = set()
                for raw in raw_items:
                    if not isinstance(raw, str):
                        continue
                    parsed = _parse_review_fields(raw)
                    txt = (parsed.get("text") or "").strip()
                    if not txt:
                        continue
                    key = _normalize_review_text(txt).lower()
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    reviews_out.append(parsed)
                    if len(reviews_out) >= mr:
                        break
            else:
                # fallback: 정상 리뷰 수집이 실패했을 때만 사용
                fallback_used = True
                all_text = page.evaluate("() => document.body.innerText")
                fallback_text = _normalize_review_text((all_text or "")[:5000])
                if fallback_text:
                    reviews_out.append(
                        {
                            "text": fallback_text,
                            "date": None,
                            "rating": None,
                            "reviewerReviewCount": None,
                            "reviewerAverageRating": None,
                        }
                    )

        except Exception as e:
            print(f"🚨 [카카오 크롤러] 에러: {e}")
            fallback_used = True
            try:
                all_text = page.evaluate("() => document.body.innerText")
                fallback_text = _normalize_review_text((all_text or "")[:5000])
                if fallback_text:
                    reviews_out = [
                        {
                            "text": fallback_text,
                            "date": None,
                            "rating": None,
                            "reviewerReviewCount": None,
                            "reviewerAverageRating": None,
                        }
                    ]
            except Exception:
                reviews_out = []
        finally:
            browser.close()

    collected_count = len(reviews_out)
    raw_count = collected_count  # 현 단계: dedupe 이후를 raw로 본다(향후 useful/used 분리는 main 단계)
    reviewer_signals = _compute_reviewer_signals(reviews_out)

    return {
        "reviews": reviews_out,
        "sourceStats": {
            "kakaoAverageRating": kakao_average_rating if isinstance(kakao_average_rating, (int, float)) else None,
            "kakaoTotalReviewCount": kakao_total_review_count if isinstance(kakao_total_review_count, int) else None,
            "rawReviewCount": int(raw_count),
            "collectedReviewCount": int(collected_count),
            "fallbackUsed": bool(fallback_used),
        },
        "reviewerSignals": reviewer_signals,
    }
