from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Iterable


def make_canonical_key(name: str, address: str) -> str:
    n = (name or "").strip().lower()
    a = (address or "").strip().lower()
    s = f"{n}|{a}"
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s가-힣|.,:/()\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:240]


def is_stale(doc_or_result: dict | None, *, days: int = 30) -> bool:
    if not isinstance(doc_or_result, dict):
        return True
    d = (doc_or_result.get("date") or "").strip()
    if not d:
        return True
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
    except Exception:
        return True
    return datetime.now() - dt >= timedelta(days=days)


def upsert_aliases(existing: dict | None, new_aliases: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    if isinstance(existing, dict):
        for x in existing.get("aliases") or []:
            if not x:
                continue
            s = str(x).strip()
            k = s.lower()
            if not s or k in seen:
                continue
            seen.add(k)
            out.append(s)

    for x in new_aliases or []:
        if not x:
            continue
        s = str(x).strip()
        k = s.lower()
        if not s or k in seen:
            continue
        seen.add(k)
        out.append(s)

    return out[:120]


def find_existing_doc(coll, canonical_name: str, canonical_key: str) -> tuple[dict | None, bool]:
    """
    Mongo 문서 조회: **name(Google resolve 공식 상호) 우선**, canonical_key는 보조(fallback).

    1) {"name": canonical_name}
    2) 없으면 {"canonical_key": canonical_key}

    Returns:
        (doc, fallback_canonical_key_found)
    """
    if coll is None:
        return None, False

    cn = (canonical_name or "").strip()
    ck = (canonical_key or "").strip()

    if cn:
        doc = coll.find_one({"name": cn})
        if doc:
            return doc, False

    if ck:
        doc = coll.find_one({"canonical_key": ck})
        if doc:
            return doc, True

    return None, False

