from __future__ import annotations

import re
from typing import Any


def normalize_review_text(text: str) -> str:
    """
    내부 판단/중복 제거용 normalize.
    - 원문을 과하게 훼손하지 않되, 중복 비교가 가능하도록 공백/기호를 정리한다.
    - 반환값은 비교용이므로, 외부 노출/저장에 그대로 쓰지 않는 것을 권장.
    """
    t = "" if text is None else str(text)
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    # 과한 특수기호/이모지류 제거(중복 비교 목적). 한글/영문/숫자/기본 구두점은 보존.
    t = re.sub(r"[^\w\s가-힣.,!?~:/()%+\-]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def get_review_text(review: str | dict) -> str:
    if isinstance(review, dict):
        v = review.get("text")
        return "" if v is None else str(v)
    return "" if review is None else str(review)


_GENERIC_SHORT_PATTERNS = frozenset(
    {
        "맛있어요",
        "맛있습니다",
        "좋아요",
        "굿",
        "최고예요",
        "최고",
        "친절해요",
        "친절합니다",
        "또 갈게요",
        "또올게요",
        "또 올게요",
        "재방문할게요",
        "재방문",
        "맛집",
        "추천",
        "강추",
        "만족",
        "만족해요",
        "대박",
    }
)


def _looks_like_only_reaction(text: str) -> bool:
    t = normalize_review_text(text)
    if not t:
        return True
    # 글자/숫자 비중이 거의 없으면(이모지/기호 위주) 반응형으로 취급
    letters = re.sub(r"[^a-z0-9가-힣]", "", t)
    if len(letters) <= 1:
        return True
    return False


def is_generic_short_review(text: str) -> bool:
    t = normalize_review_text(text)
    if not t:
        return True
    if _looks_like_only_reaction(t):
        return True
    # 너무 짧고 상투어/감탄만
    if len(t) <= 10 and t.replace(" ", "") in {p.replace(" ", "") for p in _GENERIC_SHORT_PATTERNS}:
        return True
    if len(t) <= 8 and re.fullmatch(r"[.!?~]+", t or ""):
        return True
    return False


_CONCRETE_KEYWORDS = [
    # 메뉴/음식(너무 공격적으로 빼지 않기 위해 광범위)
    "삼겹살",
    "갈비",
    "한우",
    "불고기",
    "김치찌개",
    "순두부",
    "국밥",
    "감자탕",
    "냉면",
    "칼국수",
    "라면",
    "라멘",
    "초밥",
    "회",
    "스시",
    "파스타",
    "피자",
    "스테이크",
    "버거",
    "커피",
    "디저트",
    "빙수",
    "빵",
    # 맛의 구체 표현
    "짜",
    "달",
    "맵",
    "싱겁",
    "질기",
    "부드럽",
    "신선",
    "비리",
    "잡내",
    "느끼",
    "고소",
    "국물",
    "면",
    "식감",
    # 가격/가성비/양
    "가격",
    "가성비",
    "비싸",
    "싸",
    "돈 아깝",
    "돈아깝",
    "푸짐",
    "양",
    "양이",
    "양 많",
    "양적",
    "만원",
    "원",
    # 웨이팅/시간/예약
    "웨이팅",
    "대기",
    "줄",
    "예약",
    "브레이크",
    "브레이크타임",
    "런치",
    "점심",
    "저녁",
    "오픈",
    "마감",
    "분",
    "시간",
    # 분위기/공간
    "분위기",
    "조용",
    "시끄",
    "데이트",
    "좌석",
    "테이블",
    "매장",
    "인테리어",
    "넓",
    "좁",
    # 서비스
    "서비스",
    "친절",
    "불친절",
    "응대",
    "주문",
    "누락",
    # 위생
    "위생",
    "냄새",
    "머리카락",
    "벌레",
    "청결",
    "더럽",
    # 주차
    "주차",
    "주차장",
    # 외국인/언어
    "외국인",
    "영어",
    "메뉴판",
    "언어",
    # 혼밥/인원
    "혼밥",
    "1인",
    "1 인",
    "최소 2인",
    "2인부터",
]

_PROMO_KEYWORDS = [
    "이벤트",
    "영수증",
    "리뷰 작성",
    "리뷰작성",
    "서비스 받",
    "제공받",
    "협찬",
    "광고",
    "체험단",
    "지원받",
    "sponsored",
    "ad",
    "promotion",
    "promo",
]


def _has_concrete_signal(text: str) -> bool:
    t = normalize_review_text(text)
    if not t:
        return False
    # 숫자/단위가 있으면 구체성 가능성이 높음
    if re.search(r"\d", t):
        return True
    # 키워드 기반(너무 엄격하지 않게)
    return any(k in t for k in _CONCRETE_KEYWORDS)


def _has_promo_signal(text: str) -> bool:
    t = normalize_review_text(text)
    return any(k in t for k in _PROMO_KEYWORDS) if t else False


def is_useful_review(text: str) -> bool:
    """
    useful 리뷰 판정(MVP).
    - 너무 짧고 상투적이면 drop
    - 짧아도 구체 정보가 있으면 keep 가능성 ↑
    - 광고/이벤트 문구만 반복이면 useful로 보지 않음(다만 구체 정보가 있으면 유지)
    """
    t = "" if text is None else str(text)
    nt = normalize_review_text(t)
    if not nt:
        return False

    # 길이 기반(보수적으로)
    nlen = len(nt)
    generic = is_generic_short_review(nt)
    concrete = _has_concrete_signal(nt)
    promo = _has_promo_signal(nt)

    if generic and not concrete:
        return False

    # 짧지만 구체 신호가 없으면 drop
    if nlen < 18 and not concrete:
        return False

    # 광고/이벤트만 짧게 적힌 경우 drop (구체 신호가 있으면 keep)
    if promo and not concrete and nlen < 70:
        return False

    return True


def calculate_review_pattern_stats(
    raw_reviews: list[Any], useful_reviews: list[Any], dropped_reviews: list[Any]
) -> dict:
    raw_count = len(raw_reviews) if raw_reviews else 0
    useful_count = len(useful_reviews) if useful_reviews else 0

    if raw_count <= 0:
        return {
            "shortReviewRatio": 0.0,
            "usefulReviewRatio": 0.0,
            "eventKeywordRatio": 0.0,
            "duplicateLikeRatio": 0.0,
            "averageReviewLength": 0.0,
        }

    short_generic = 0
    event_hit = 0
    norm_lengths = []
    seen = set()
    dup_count = 0

    for r in raw_reviews:
        txt = get_review_text(r)
        nt = normalize_review_text(txt)
        norm_lengths.append(len(nt))
        if is_generic_short_review(nt):
            short_generic += 1
        if _has_promo_signal(nt):
            event_hit += 1
        if nt:
            if nt in seen:
                dup_count += 1
            else:
                seen.add(nt)

    avg_len = sum(norm_lengths) / len(norm_lengths) if norm_lengths else 0.0

    return {
        "shortReviewRatio": round(short_generic / raw_count, 4),
        "usefulReviewRatio": round(useful_count / raw_count, 4),
        "eventKeywordRatio": round(event_hit / raw_count, 4),
        "duplicateLikeRatio": round(dup_count / raw_count, 4),
        "averageReviewLength": round(float(avg_len), 2),
    }


def filter_useful_reviews(raw_reviews: list[Any]) -> dict:
    """
    입력 형태:
    - list[str]
    - list[dict] (scraper 구조: {"text": ..., "date": ..., ...})

    출력:
    - 원본 형태를 최대한 유지
    - 중복 제거는 normalize된 text 기준(첫 등장만 유지)
    """
    raw_reviews = list(raw_reviews or [])

    useful: list[Any] = []
    dropped: list[Any] = []

    seen_norm: set[str] = set()
    short_generic_count = 0

    for r in raw_reviews:
        txt = get_review_text(r)
        nt = normalize_review_text(txt)
        if not nt:
            dropped.append(r)
            continue

        # duplicate 제거(첫 번째만 남김)
        if nt in seen_norm:
            dropped.append(r)
            continue
        seen_norm.add(nt)

        if is_generic_short_review(nt):
            short_generic_count += 1

        if is_useful_review(nt):
            useful.append(r)
        else:
            dropped.append(r)

    stats = calculate_review_pattern_stats(raw_reviews, useful, dropped)
    return {
        "raw_reviews": raw_reviews,
        "useful_reviews": useful,
        "dropped_reviews": dropped,
        "rawReviewCount": len(raw_reviews),
        "usefulReviewCount": len(useful),
        "droppedReviewCount": len(dropped),
        "reviewPatternStats": stats,
    }


def _quick_test_samples() -> None:
    # 테스트 샘플(요구사항)
    assert is_useful_review("맛있어요") is False
    assert is_useful_review("굿") is False
    assert is_useful_review("삼겹살은 맛있는데 웨이팅이 길고 가격은 조금 비싸요") is True
    assert is_useful_review("분위기는 조용해서 데이트하기 좋고 주차는 힘들어요") is True

    assert (
        is_useful_review(
            get_review_text(
                {"text": "맛있어요", "reviewerReviewCount": 200, "reviewerAverageRating": 3.5}
            )
        )
        is False
    )
    assert (
        is_useful_review(
            get_review_text(
                {
                    "text": "라멘 국물이 진하고 면 식감은 좋은데 점심 웨이팅이 길어요",
                    "reviewerReviewCount": 50,
                    "reviewerAverageRating": 3.8,
                }
            )
        )
        is True
    )


if __name__ == "__main__":
    _quick_test_samples()

