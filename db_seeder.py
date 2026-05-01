"""
서울 주요 상권 식당 정보를 카카오 로컬 API로 수집해 MongoDB에 적재하는 시드 스크립트.

실행 전 프로젝트 루트 `.env`에 `KAKAO_API_KEY`, `MONGO_URI`를 설정하세요.
"""

import os
import sys
import time

import pymongo
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# ---------------------------------------------------------------------------
# 고정 설정
# ---------------------------------------------------------------------------
DB_NAME = "zzinview_db"
COLLECTION_NAME = "places"

TARGET_QUERIES = [
    "강남역 맛집",
    "성수동 맛집",
    "홍대 맛집",
    "연남동 맛집",
    "청담동 파인다이닝",
]

KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
MAX_PAGE = 3
SLEEP_SEC = 0.5


def fetch_places_for_query(session: requests.Session, query: str, page: int) -> list[dict]:
    """카카오 키워드 검색 한 페이지. 실패 시 빈 리스트."""
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "query": query,
        "category_group_code": "FD6",
        "page": page,
        "size": 15,
    }
    try:
        r = session.get(KAKAO_KEYWORD_URL, headers=headers, params=params, timeout=15)
        if r.status_code != 200:
            print(f"    ⚠️ API HTTP {r.status_code} (query={query!r}, page={page})")
            return []
        data = r.json()
        return data.get("documents") or []
    except Exception as e:
        print(f"    ⚠️ 요청 실패 (query={query!r}, page={page}): {e}")
        return []


def pick_address(doc: dict) -> str:
    road = (doc.get("road_address_name") or "").strip()
    jibun = (doc.get("address_name") or "").strip()
    return road if road else jibun


def main() -> None:
    kakao_ok = KAKAO_API_KEY is not None and str(KAKAO_API_KEY).strip() != ""
    mongo_ok = MONGO_URI is not None and str(MONGO_URI).strip() != ""
    if not kakao_ok or not mongo_ok:
        print("❌ .env 파일에 KAKAO_API_KEY와 MONGO_URI를 설정해주세요.")
        sys.exit(1)

    print("=" * 60)
    print("🌱 ZzinView DB Seeder — 카카오 로컬 → MongoDB")
    print(f"   DB: {DB_NAME} / 컬렉션: {COLLECTION_NAME}")
    print(f"   타겟 쿼리 수: {len(TARGET_QUERIES)} (페이지 1~{MAX_PAGE} / FD6)")
    print("=" * 60)

    client = pymongo.MongoClient(MONGO_URI)
    coll = client[DB_NAME][COLLECTION_NAME]

    inserted_total = 0
    skipped_dup = 0
    session = requests.Session()

    for region_query in TARGET_QUERIES:
        print(f"\n🔎 검색 시작: {region_query!r}")
        for page in range(1, MAX_PAGE + 1):
            print(f"   📄 페이지 {page}/{MAX_PAGE} 요청 중…")
            docs = fetch_places_for_query(session, region_query, page)
            time.sleep(SLEEP_SEC)

            if not docs:
                print(f"      (문서 없음 또는 오류 — 다음 페이지/지역으로)")
                continue

            for doc in docs:
                place_name = (doc.get("place_name") or "").strip()
                address = pick_address(doc)
                if not place_name:
                    print(f"      ⏭️ 상호 없음 — 스킵")
                    continue

                existing = coll.find_one({"name": place_name})
                if existing:
                    print(f"      ⏭️ 중복 패스: {place_name!r}")
                    skipped_dup += 1
                    continue

                payload = {
                    "name": place_name,
                    "address": address,
                    "isAnalyzed": False,
                }
                coll.insert_one(payload)
                inserted_total += 1
                addr_preview = (address[:50] + "…") if len(address) > 50 else address
                print(f"      ✅ DB 저장: {place_name!r} | {addr_preview!r}")

            if len(docs) < 15:
                print(f"   ℹ️ 마지막 페이지로 보임(결과 {len(docs)}건) — 이 쿼리 종료")
                break

        print(f"   ⏳ 지역 간 대기 {SLEEP_SEC}s…")
        time.sleep(SLEEP_SEC)

    client.close()
    print("\n" + "=" * 60)
    print(f"🎉 완료 — 신규 insert: {inserted_total}건 | 중복 스킵: {skipped_dup}건")
    print("=" * 60)


if __name__ == "__main__":
    main()
