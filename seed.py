from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Iterable

from scraper import search_and_get_reviews

# We intentionally reuse internal pipeline functions without running FastAPI.
# NOTE: importing main will initialize Mongo/OpenAI clients; it will NOT start a server
# because uvicorn.run is guarded by if __name__ == "__main__".
import main as backend
from canonical import make_canonical_key, is_stale, upsert_aliases, find_existing_doc


def _today_ymd() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def build_fast_result(place_info: dict, ai_data: dict, lang: str) -> dict:
    """
    /api/analyze의 fast 결과 구조와 최대한 유사하게 만든다.
    - seed는 유저 과금/에너지 카운트를 건드리지 않는다.
    """
    final_result = {
        **ai_data,
        "name": ai_data.get("translatedName") or place_info.get("name", ""),
        "address": place_info.get("address", ""),
        "rating": place_info.get("rating", 0),
        "isNewDiscovery": False,
        "has_advanced": False,
    }
    return final_result


def _read_seed_queries(input_path: str) -> list[str]:
    p = (input_path or "").strip()
    if not p:
        raise ValueError("Missing --input path.")
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"Input file not found: {p}\n"
            "Create one of these:\n"
            "- seed_queries.csv: one query per line (optionally with a header 'query')\n"
            "- seed_queries.json: [\"성수 감자탕\", \"홍대 삼겹살\", ...]\n"
        )

    if p.lower().endswith(".json"):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
        raise ValueError("JSON must be a list of strings.")

    if p.lower().endswith(".csv"):
        out: list[str] = []
        with open(p, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                q = (row[0] or "").strip()
                if not q:
                    continue
                if q.lower() == "query":
                    continue
                out.append(q)
        return out

    # fallback: treat as text file
    with open(p, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f.readlines() if ln.strip()]


def _parse_langs(s: str) -> list[str]:
    raw = [x.strip() for x in (s or "").split(",") if x.strip()]
    langs = [x for x in raw if x in ("ko", "en")]
    return langs or ["ko"]


def seed_one_place(
    seed_query: str,
    *,
    langs: list[str],
    force: bool,
    dry_run: bool,
    stale_days: int,
) -> None:
    coll = backend.collection
    if coll is None and not dry_run:
        raise RuntimeError("Mongo collection is not available (check MONGO_URI).")

    # 1) Google resolve (canonical)
    place_info = search_and_get_reviews(seed_query)
    if not place_info:
        print(f"[SKIP] seed_query={seed_query!r} -> Google resolve 실패")
        return

    canonical_name = (place_info.get("name") or "").strip()
    canonical_address = (place_info.get("address") or "").strip()
    if not canonical_name:
        print(f"[SKIP] seed_query={seed_query!r} -> Google resolve 후 name이 비어 있음")
        return

    canonical_key = make_canonical_key(canonical_name, canonical_address)

    existing_doc = None
    fallback_canonical_key_found = False
    if coll is not None:
        existing_doc, fallback_canonical_key_found = find_existing_doc(
            coll, canonical_name, canonical_key
        )

    existing_found = bool(existing_doc)

    alias_seeds = [
        seed_query,
        canonical_name,
        backend.clean_place_name(canonical_name),
    ]
    if existing_doc and fallback_canonical_key_found:
        old_name = (existing_doc.get("name") or "").strip()
        if old_name and old_name.lower() != canonical_name.lower():
            alias_seeds.append(old_name)
    aliases = upsert_aliases(existing_doc, alias_seeds)

    print("=" * 80)
    print(f"seed_query: {seed_query}")
    print(f"canonical_name: {canonical_name}")
    print(f"canonical_address: {canonical_address}")
    print(f"canonical_key: {canonical_key}")
    print(f"lookup_primary: name")
    print(f"fallback_canonical_key_found: {fallback_canonical_key_found}")
    print(f"aliases: {aliases}")
    print(f"existing_doc_found: {existing_found}")

    # 2) Ensure base doc exists / canonical fields (primary: name == canonical_name)
    base_doc_update = {
        "name": canonical_name,
        "canonical_name": canonical_name,
        "address": canonical_address,
        "canonical_address": canonical_address,
        "canonical_key": canonical_key,
        "aliases": aliases,
    }

    if dry_run:
        print("[DRY-RUN] base doc upsert 예정 (filter: {\"name\": canonical_name})")
    else:
        if coll is not None:
            if existing_doc:
                coll.update_one({"_id": existing_doc["_id"]}, {"$set": base_doc_update})
            else:
                coll.update_one({"name": canonical_name}, {"$set": base_doc_update}, upsert=True)

    # re-fetch doc for decision making (non dry-run only)
    doc = existing_doc
    if not dry_run and coll is not None:
        doc = coll.find_one({"name": canonical_name})

    # 3) Fast analysis 저장 (lang별)
    fast_actions: list[str] = []
    for lang in langs:
        key = f"result_{lang}"
        needs = force or not isinstance(doc, dict) or not doc.get(key) or is_stale(doc, days=stale_days)
        if not needs:
            fast_actions.append(f"{lang}:skip")
            continue

        if dry_run:
            fast_actions.append(f"{lang}:would_create")
            continue

        try:
            prompt = backend.get_fast_prompt(lang, place_info)
            resp = backend.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a JSON generating assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            ai_data = json.loads(resp.choices[0].message.content)
            ai_data = backend.sanitize_ai_result(ai_data, "fast")
            final_result = build_fast_result(place_info, ai_data, lang)
            update = {
                "date": _today_ymd(),
                key: final_result,
                # 초기 상태: 고급 분석은 별도 단계에서 채움
                f"kakao_result_{lang}": (doc or {}).get(f"kakao_result_{lang}") or {"status": "processing"},
            }
            if coll is not None:
                coll.update_one({"name": canonical_name}, {"$set": update}, upsert=True)
            fast_actions.append(f"{lang}:created")
        except Exception as e:
            fast_actions.append(f"{lang}:error")
            print(f"[FAST ERROR] lang={lang} seed_query={seed_query!r}: {e}")

    print(f"fast_result: {', '.join(fast_actions) if fast_actions else 'none'}")

    # refresh doc
    if not dry_run and coll is not None:
        doc = coll.find_one({"name": canonical_name})

    # 4) Kakao advanced analysis 저장 (lang별)
    kakao_actions: list[str] = []
    for lang in langs:
        kkey = f"kakao_result_{lang}"
        kdoc = (doc or {}).get(kkey) if isinstance(doc, dict) else None
        status = kdoc.get("status") if isinstance(kdoc, dict) else None
        needs = force or not isinstance(kdoc, dict) or status != "ok" or is_stale(doc, days=stale_days)
        if not needs:
            kakao_actions.append(f"{lang}:skip(ok)")
            continue

        if dry_run:
            kakao_actions.append(f"{lang}:would_create(precompute)")
            continue

        try:
            # run_kakao_advanced_analysis writes DB internally (kakao_result_{lang}, maybe map_flag)
            backend.run_kakao_advanced_analysis(
                canonical_name,
                canonical_name,
                canonical_address,
                lang,
                precompute=True,
                max_reviews=100,
            )
            kakao_actions.append(f"{lang}:done")
        except Exception as e:
            kakao_actions.append(f"{lang}:error")
            print(f"[KAKAO ERROR] lang={lang} seed_query={seed_query!r}: {e}")

    print(f"kakao_result: {', '.join(kakao_actions) if kakao_actions else 'none'}")

    # 5) 출력용 최종 상태 요약(가능하면)
    kakao_matched_name = ""
    kakao_matched_address = ""
    useful_cnt = None
    data_conf = ""
    map_flag_saved = False
    if not dry_run and coll is not None:
        doc2 = coll.find_one({"name": canonical_name}) or {}
        map_flag_saved = bool(doc2.get("map_flag"))
        kd = (doc2.get(f"kakao_result_{langs[0]}") if langs else None) or {}
        if isinstance(kd, dict):
            kakao_matched_name = str(kd.get("kakao_matched_name") or "")
            kakao_matched_address = str(kd.get("kakao_matched_address") or "")
            ss = kd.get("sourceStats") if isinstance(kd.get("sourceStats"), dict) else {}
            if isinstance(ss, dict):
                useful_cnt = ss.get("usefulReviewCount")
            data_conf = str(kd.get("dataConfidence") or "")
            status = str(kd.get("status") or "")

        print(f"kakao_matched_name: {kakao_matched_name}")
        print(f"kakao_matched_address: {kakao_matched_address}")
        print(f"status: {status}")
        print(f"usefulReviewCount: {useful_cnt}")
        print(f"dataConfidence: {data_conf}")
        print(f"map_flag_saved: {map_flag_saved}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ZzinView precompute seed (Google->Fast->Kakao Advanced)")
    parser.add_argument("--input", required=True, help="seed_queries.csv or seed_queries.json")
    parser.add_argument("--langs", default="ko,en", help="comma-separated: ko,en")
    parser.add_argument("--limit", type=int, default=0, help="0 means no limit")
    parser.add_argument("--dry-run", action="store_true", help="no DB writes, no OpenAI calls")
    parser.add_argument("--force", action="store_true", help="recompute even if recent cache exists")
    parser.add_argument("--stale-days", type=int, default=30, help="cache freshness window in days")
    parser.add_argument("--sleep", type=float, default=0.5, help="sleep seconds between places")
    args = parser.parse_args()

    langs = _parse_langs(args.langs)
    queries = _read_seed_queries(args.input)
    if args.limit and args.limit > 0:
        queries = queries[: args.limit]

    print("=" * 80)
    print("ZzinView seed/precompute")
    print(f"input: {args.input}")
    print(f"langs: {langs}")
    print(f"limit: {len(queries)}")
    print(f"dry_run: {args.dry_run}")
    print(f"force: {args.force}")
    print(f"stale_days: {args.stale_days}")
    print("=" * 80)

    for i, q in enumerate(queries, start=1):
        try:
            print(f"\n[{i}/{len(queries)}] start")
            seed_one_place(
                q,
                langs=langs,
                force=bool(args.force),
                dry_run=bool(args.dry_run),
                stale_days=int(args.stale_days),
            )
        except Exception as e:
            print(f"[PLACE ERROR] seed_query={q!r}: {e}")
        time.sleep(max(0.0, float(args.sleep)))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

