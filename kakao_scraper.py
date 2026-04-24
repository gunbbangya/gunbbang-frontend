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


def get_kakao_place_id(place_name: str, google_address: str):
    """
    키워드 검색 후, **구글 address**와 토큰(시·구·동·번지) 교차로 가장 잘 맞는 후보를 고른다.
    응답이 비면 None.
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
        if not google_address or not str(google_address).strip():
            return docs[0]["id"]

        best_doc = max(
            docs, key=lambda d: _doc_rank_key(google_address, d, place_name)
        )
        rk = _doc_rank_key(google_address, best_doc, place_name)
        a1 = (best_doc.get("address_name") or "").strip()
        a2 = (best_doc.get("road_address_name") or "").strip()
        pname = (best_doc.get("place_name") or "").strip()
        print(
            f"🎯 [카카오 주소교차] 쿼리='{place_name[:60]}' → "
            f"선택(주소겹침 {rk[0]}·상호가산 {rk[1]}) {pname} / {a1 or a2}"
        )
        if len(docs) > 1 and rk[0] == 0 and _addr_tokens(google_address):
            print(
                f"   ⚠️ [카카오] Google 주소 토큰 겹침 0 — 상호/도로·지번 토큰으로 최적 후보를 고름"
            )

        return best_doc["id"]

    except Exception as e:
        print(f"🚨 카카오 ID 검색 실패: {e}")
    return None


# 2. 플레이라이트로 카카오 리뷰 25개 긁어오는 함수
def get_deep_kakao_reviews(place_id: str):
    reviews = []
    place_url = f"https://place.map.kakao.com/{place_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        review_direct_url = f"{place_url}#review"
        print(f"🕵️‍♂️ [카카오 크롤러] 출동: {review_direct_url}")

        try:
            page.goto(review_direct_url)
            time.sleep(3)

            for _ in range(3):
                page.mouse.wheel(0, 800)
                time.sleep(1)

            try:
                more_buttons = page.get_by_text("더보기", exact=True)
                for i in range(more_buttons.count()):
                    more_buttons.nth(i).click(timeout=1000)
                    time.sleep(0.5)
            except Exception:
                pass

            extracted_reviews = page.evaluate("""() => {
                const lis = Array.from(document.querySelectorAll('li'));
                const reviewLis = lis.filter(li => /\\d{4}\\.\\d{2}\\.\\d{2}\\./.test(li.innerText));
                return reviewLis.map(li => li.innerText.trim());
            }""")

            if extracted_reviews:
                for text in extracted_reviews[:25]:
                    clean_text = " ".join(text.split("\n"))
                    reviews.append(clean_text)
            else:
                all_text = page.evaluate("() => document.body.innerText")
                reviews.append(all_text[:5000])

        except Exception as e:
            print(f"🚨 [카카오 크롤러] 에러: {e}")
        finally:
            browser.close()

    return reviews
