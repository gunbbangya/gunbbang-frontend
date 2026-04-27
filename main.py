import os
import json
import time
import re
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews 
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
from openai import OpenAI
import threading
import random
from kakao_scraper import get_kakao_place_id, get_deep_kakao_reviews 

load_dotenv()

# ==========================================
# 💡 OpenAI & MongoDB 설정
# ==========================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MONGO_URI = os.getenv("MONGO_URI")
try:
    mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = mongo_client["jjin_view_db"]
    collection = db["places_cache"]
    print("✅ MongoDB 클라우드 연결 성공!")
except Exception as e:
    print(f"🚨 MongoDB 연결 실패: {e}")
    collection = None

last_queries = {} 
user_requests = defaultdict(list)
RATE_LIMIT = 1500 
WINDOW_SECONDS = 86400


def _prune_analyze_requests(client_ip: str) -> None:
    now = time.time()
    user_requests[client_ip] = [t for t in user_requests[client_ip] if now - t < WINDOW_SECONDS]


def analyze_rate_limit_allows(client_ip: str) -> bool:
    """일일 한도 미만이면 True (아직 과금 전 검사 전용)."""
    _prune_analyze_requests(client_ip)
    return len(user_requests[client_ip]) < RATE_LIMIT


def record_chargeable_analyze(client_ip: str) -> None:
    """구글 크롤 + OpenAI 1차 분석이 성공적으로 끝난 경우에만 1회 과금."""
    _prune_analyze_requests(client_ip)
    user_requests[client_ip].append(time.time())


def extract_restaurant_tags(review_text: str) -> list[str]:
    """룰 기반 키워드 분류 — 비용 없음. 리뷰·요약·상호 등 합친 문자열에 사용."""
    if not review_text or not str(review_text).strip():
        return []

    text = str(review_text)
    tags: list[str] = []
    seen: set[str] = set()
    low = text.lower()

    def add(tag: str) -> None:
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)

    # 음식
    food_rules = [
        (["삼겹살", "고기", "돼지", "삼겹", "목살", "갈비", "소고기", "구이", "한우", "pork", "bbq", "grill", "beef"], "고기"),
        (["파스타", "피자", "스테이크", "양식", "브런치", "risotto", "pasta", "burger"], "양식"),
        (["국밥", "찌개", "된장", "김치찌개", "순두부", "탕", "설렁탕", "감자탕", "해장"], "한식"),
        (["초밥", "사시미", "회", "스시", "라멘", "돈카츠", "우동", "sushi", "ramen"], "일식"),
        (["중식", "짜장", "마라", "탕수육", "짬뽕", "dim sum"], "중식"),
        (["치킨", "닭갈비", "양념치킨", "후라이드", "chicken"], "치킨"),
        (["카페", "커피", "디저트", "케이크", "브런치", "cafe", "coffee", "dessert"], "카페·디저트"),
    ]
    for keywords, label in food_rules:
        if any((k in text) or (k.lower() in low) for k in keywords):
            add(label)

    # 분위기
    vibe_rules = [
        (["조용", "데이트", "분위기 좋", "로맨틱", "프라이빗", "조용한", "quiet", "date night", "romantic"], "조용한 데이트"),
        (["시끄", "회식", "북적", "활기", "붐비", "소란", "noisy", "crowded", "loud"], "시끌벅적한"),
    ]
    for keywords, label in vibe_rules:
        if any((k in text) or (k.lower() in low) for k in keywords):
            add(label)

    # 상황 / 페인포인트
    pain_rules = [
        (["웨이팅", "대기", "줄서", "줄 서", "줄이", "waiting", "queue", "line up"], "웨이팅 심함"),
        (["비싸", "가격", "부담", "가격이", "expensive", "overpriced", "pricey"], "가격 부담"),
        (["주차", "주차장", "parking"], "주차 불편"),
        (["위생", "벌레", "이물", "hygiene", "dirty", "hair in"], "위생 이슈"),
    ]
    for keywords, label in pain_rules:
        if any((k in text) or (k.lower() in low) for k in keywords):
            add(label)

    return tags


def build_alternative_query(
    lang: str,
    tags: list[str],
    real_score: float,
    details: dict | None,
    _place_name: str,
) -> dict:
    """상황·태그·점수 기반 대체 추천용 메타 (DB 검색은 추후 연동)."""
    details = details or {}
    try:
        t_time = float(details.get("time", 3) or 3)
    except (TypeError, ValueError):
        t_time = 3.0
    try:
        t_value = float(details.get("value", 3) or 3)
    except (TypeError, ValueError):
        t_value = 3.0

    food_order = ["고기", "양식", "한식", "일식", "중식", "치킨", "카페·디저트"]
    target_category = next((x for x in food_order if x in tags), "맛집")

    waiting_signal = "웨이팅 심함" in tags or t_time <= 2.5

    if lang == "en":
        if waiting_signal and "고기" in tags:
            suggest = "Worried about infamous wait times at meat & grill spots here?"
            avoid = "waiting"
        elif waiting_signal:
            suggest = "Is the long wait here a deal-breaker?"
            avoid = "waiting"
        elif "시끌벅적한" in tags and "조용한 데이트" in tags:
            suggest = "Want a date night without the noise and crowd?"
            avoid = "noise"
        elif real_score < 2.8:
            suggest = "Looking for a safer bet with stronger review signals?"
            avoid = "low score"
        elif t_value <= 2.5:
            suggest = "Want similar food with better value for money?"
            avoid = "value"
        else:
            suggest = "Explore other verified picks nearby in the same vein."
            avoid = ""
    else:
        if waiting_signal and "고기" in tags:
            suggest = "이곳의 악명 높은 웨이팅이 걱정되시나요?"
            avoid = "웨이팅"
        elif waiting_signal:
            suggest = "여기 웨이팅·대기가 부담스러우신가요?"
            avoid = "웨이팅"
        elif "시끌벅적한" in tags and "조용한 데이트" in tags:
            suggest = "데이트인데 시끄러운 곳은 피하고 싶으시죠?"
            avoid = "소음"
        elif real_score < 2.8:
            suggest = "평점이 조금 불안하다면, 같은 분야의 검증 맛집은 어떠세요?"
            avoid = "낮은 평가"
        elif t_value <= 2.5:
            suggest = "가격 부담이 크다고 느끼셨나요? 비슷한 메뉴를 더 합리적으로 즐길 수 있어요."
            avoid = "가성비"
        else:
            suggest = "비슷한 분위기·메뉴의 다른 검증 맛집도 둘러볼까요?"
            avoid = ""

    qparts = [target_category] + ([avoid] if avoid else [])
    return {
        "suggest_message": suggest,
        "target_category": target_category,
        "avoid": avoid,
        "query_hint": " ".join(qparts).strip(),
    }


def attach_tags_and_plan_b(
    payload: dict,
    lang: str,
    text_parts: list,
    score: float,
    details: dict | None,
    display_name: str,
) -> None:
    blob = " ".join(str(p) for p in text_parts if p is not None and str(p).strip())
    tags = extract_restaurant_tags(blob)
    payload["tags"] = tags
    payload["alternative_query"] = build_alternative_query(lang, tags, float(score or 0), details, display_name)


# ==========================================
# 💡 프롬프트 설정 ('파괴'라는 단어 삭제, 점수 낮추기로 완화)
# ==========================================
def get_fast_prompt(lang, place_info):
    if lang == "en":
        instruction = (
            "You are a 'First-Line Fake Review Detector'. Base score is 2.5. "
            "details.taste and details.value MUST be JSON float numbers from 1.0 to 5.0, never 0, never strings."
        )
        guidelines = """
        [Detection & Scoring Logic]
        1. Pattern Recognition: If keywords or hashtags repeat unnaturally, increase 'eventProbability'.
        2. Strict 'Fatal Flaw' (Score Eraser): Only [Poor Hygiene (bugs, hair), Extreme Rudeness (insults, ignoring customers), Spoiled Food] are fatal. Slash the score only for these.
        3. Reference Info (Include in Summary): Expensive prices, long waiting times, and parking issues are NOT fatal flaws. Do NOT slash scores for these, but ALWAYS mention them in the summary as 'reference info' so users can be prepared.
        4. NO USERNAMES: Never mention specific nicknames or usernames found in reviews. Use generic terms like 'some visitors'.

        [MANDATORY — Contextual inference for food reviews; NEVER use 0 for taste or value]
        - Do NOT look only for the literal words "taste" or "value/price." Infer from CONTEXT. Every restaurant review implies food quality and value in some way.
        - TASTE (taste): Any description of food quality counts—e.g. salty, sweet, tough, fresh, delicious, "best ever", texture, flavor, menu quality, "would order again", complaints about the food itself. Map positive → higher scores, negative → lower, always within 1.0–5.0.
        - VALUE (value): Any price/portion/satisfaction signal counts—e.g. expensive, cheap, small portions, "not worth it", "great deal", "generous", money's worth, cost vs. quality. Again 1.0–5.0 from context, not keyword search.
        - For a restaurant, taste and value CANNOT be "missing" from the analysis. If explicit mentions are thin, still infer a reasonable 1.0–5.0 from overall tone. NEVER output 0 for taste or value.
        - If some OTHER dimension (e.g. wait time) is hardly mentioned, use a neutral default of 3.0 for that dimension only—not 0, and never 0 for taste or value.
        - JSON: All detail scores must be actual JSON float numbers, not strings, e.g. "taste": 4.2 (numeric), never "taste": "4" or "0".
        """
        json_format = (
            '{ "translatedName": "Name", "translatedAddress": "Address", "realScore": 1.0, "eventProbability": 0, '
            '"aiSummary": "text", "details": { '
            '"taste": 4.2, "value": 3.5, "service": 3.0, "time": 3.0, "hygiene": 3.0 } }  '
            '(realScore 1.0-5.0; details: each key is a number 1.0-5.0, floats only; taste & value are NEVER 0.0;'
            " use 3.0 for weakly specified non-taste fields only.)"
        )
    else:
        instruction = (
            "당신은 5개의 리뷰에서 조작 패턴을 찾아내는 '1차 필터링 요원'입니다. 기준점은 2.5점입니다. "
            "details의 taste, value는 반드시 1.0~5.0 **실수(JSON 숫자)**; 0이나 문자열로 반환 절대 금지."
        )
        guidelines = """
        [🔍 1차 방어선 감지 및 채점 논리]
        1. 앵무새 패턴 감지: 특정 키워드나 해시태그가 반복되면 조작 확률(eventProbability)을 높이세요.
        2. 치명적 결함(점수 감점 기준): 오직 [위생 불량(벌레, 이물질), 심각한 불친절(욕설, 반말, 손님 무시), 상한 음식]만 치명적 결함으로 간주하여 점수를 대폭 낮춥니다.
        3. 필수 참고 정보(요약 포함): 비싼 가격, 긴 웨이팅, 주차 불편은 '치명적 결함'이 아닙니다. 이를 이유로 점수를 대폭 깎지 마세요. 대신, 사용자가 참고할 수 있도록 요약문에 반드시 해당 내용(가격/웨이팅/주차 등)을 포함하여 서술하세요.
        4. 닉네임 언급 금지: 리뷰어의 닉네임이나 실명을 절대 직접 언급하지 마세요. '방문객들', '실사용자' 등의 표현을 사용하세요.

        [필수 — 식당 리뷰 문맥 추론; taste·value는 0점 절대 금지]
        - 리뷰에 "맛" "가성비"라는 단어가 **직접** 없어도 문맥을 읽어 점수를 매겨라. 키워드 매칭이 아니다.
        - 맛(taste): "짜다, 달다, 질기다, 싱겁다, 쫄깃하다, 부드럽다, 비린내, 신선, 존맛, JMT, 입맛, 푸짐(맛 중심)" 등 **음식 품질·맛**에 관한 모든 서술은 taste 평가다. 반드시 1.0~5.0 (소수)로.
        - 가성비(value): "비싸다, 쌈다, 양이 적다, 푸짐하다, 돈 아깝다, 혜자, 이 가격이면" 등 **가격·양·이만한 값**에 관한 서술은 value 평가다. 역시 1.0~5.0, 절대 0 아님.
        - 음식점 맛(taste)과 가성비(value)는 논리상 리뷰가 있으면 반드시 추론 가능하다. 정보가 희박하면 **전체 톤**에서 추정하라. **taste와 value에 0.0을 출력하는 것은 금지**다.
        - "맛/가성비" 외 항목(대기, 서비스만 언급 등)이 거의 없을 때만, 그 **해당 축**에 한해 3.0 **기본 점**을 쓸 수 있다. 0.0이 아니다.
        - JSON의 details.* 점수는 **반드시 숫자형(실수)**. 예: "taste": 4.5 — 따옴표로 감싼 문자열 금지. 0이 아닌 1.0~5.0.
        """
        json_format = (
            '{ "translatedName": "가게 이름", "translatedAddress": "가게 주소", "realScore": 1.0, "eventProbability": 0, '
            '"aiSummary": "…", "details": { "taste": 4.2, "value": 3.5, "service": 3.0, "time": 3.0, "hygiene": 3.0 } }  '
            "(realScore 1.0-5.0; details는 각각 1.0-5.0 **실수**; taste·value는 **절대 0.0 사용 금지**;"
            " 언급 없는 사소 항목만 3.0 기본.)"
        )
    
    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nInput Data: Name: {place_info['name']}\nReviews: {' '.join(place_info['reviews'])}"

def get_deep_prompt(lang, place_name, reviews):
    reviews_text = "\n".join(reviews)
    technical_json = """
        [Technical — scores & JSON typing]
        details.taste and details.value: JSON floats 1.0–5.0 only, NEVER 0.0 (infer from context if thin). Other axes can default to 3.0 if unmentioned—not 0.0.
        realScore: float 1.0–5.0. eventProbability: integer.
        romanizedName: required string — Revised Romanization of the venue Korean name so visitors can navigate (not a poetic English translation).
    """
    if lang == "en":
        instruction = (
            "You are a concise local gastronomy writer for foreigners visiting Korea, based on Kakao-place reviews only. Base score is 2.5. "
            "details.taste and details.value MUST be JSON floats 1.0–5.0, never 0.0 (infer from thin context)."
        )
        guidelines = """
        [Tone & role — replace 'fake-review sentinel' mentality]
        1) Role: Practical, dry, factual—like a local food guide handout for travelers/couples. No literary fluff. Deliver what matters to plan a meal.
        2) Content priority FIRST in aiSummary: (a) must-try dishes/menu items diners praise, (b) wait-time tips/best timing, (c) vibe/ambiance. Fold hygiene only as clear warnings where relevant.
        3) Downsides objectively: Grave issues (severe hygiene spoilage etc.) warn plainly. Ordinary gripes phrase as Things to note (e.g. "some diners found prices steep") — not melodrama.
        4) romanizedName MUST be Revised Romanization of the venue name shown in Kakao/for navigation (Gamjatang, Mukja), NOT the meaning translated into unrelated English phrases (reject style like "Spicy Pork Bone Stew" as romanizedName). Menu names cited in Korean may be romanized the same way in the prose.
        NO nicknames/usernames—use neutral terms.

        """
        guidelines = guidelines.strip() + "\n" + technical_json
        json_format = (
            '{ "realScore": 4.1, "eventProbability": 15, '
            '"romanizedName": "Gamjatang", '
            '"aiSummary": "[🔍 Insight] concise facts + vibe + must-tries ; [💡 Practical note] waits/timing + one tip", '
            '"details": { "taste": 4.2, "value": 3.8, "service": 3.0, "time": 3.0, "hygiene": 3.0 } } '
            '(All numeric scores are JSON numbers, not strings; taste/value never 0.0.)'
        )
    else:
        instruction = (
            "당신은 한국을 방문한 외국인 여행자·커플에게 **실무적으로** 도움이 되도록 카카오 리뷰만 근거로 짧게 쓰는 현지 미식 안내 에디터입니다. 기준점 2.5. "
            "taste, value는 1.0~5.0 **실수(JSON)**; **0.0 금지**."
        )
        guidelines = """
        [톤·역할 — '조작 감시' 톤 폐기]
        1) 역할: 문학적 과장 없이 건조·정확. 외국인이 메뉴·웨이팅·분위기를 현장에서 재현할 수 있게 돕는 로컬 가이드.
        2) 요약(aiSummary)의 최우선: (①) 극찬하는 **추천 메뉴·Must-try**, (②) 웨이팅·방문 시간대 등 **실전 팁**, (③) 매장 **분위기(Vibe)**. 위생 등 치명적 이슈는 필요할 때만 경고 형태로 포함.
        3) 단점: 위생 불량 등 **치명적** 문제는 명확히. 단순 불만은 "일부 방문객은 가격이 비싸다고 느낌"처럼 **참고사항(Things to note)** 톤.
        4) 로마자(romanizedName): 가게 이름·메뉴를 영작 **의역**하지 말고, 한글 발음을 **통용 로마자 표기**(가제 → Gaje, 감자탕 → Gamjatang)로 부여하여 길 찾기·통역에 적합하게. 번역 타입 이름을 romanizedName에 넣지 말 것.

        닉네임 금지. '일부 방문자' 등 표현 사용.

        """
        guidelines = guidelines.strip() + "\n" + technical_json
        json_format = (
            '{ "realScore": 4.0, "eventProbability": 12, '
            '"romanizedName": "Gamjatang", '
            '"aiSummary": "[🔍 심층 분석] … [💡 실전 꿀팁] … (두 블록, 구두 닉네임 없음)", '
            '"details": { "taste": 4.1, "value": 3.7, "service": 3.0, "time": 3.0, "hygiene": 3.0 } } '
            "(scores는 숫자 실수 필드만; taste·value=0.0 불가)"
        )

    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nTarget: {place_name}\nReviews: {reviews_text}"

app = FastAPI()

@app.middleware("http")
async def limit_requests(request: Request, call_next):
    # /api/analyze 과금은 Mongo 캐시 미스 + OpenAI 성공 시에만 record_chargeable_analyze 로 처리 (캐시 히트는 미과금).
    return await call_next(request)

ALLOWED_ORIGINS = [
    "https://gunbbang-frontend.vercel.app", 
    "http://localhost:3000",        
    "https://zzinview.app",        
    "https://www.zzinview.app"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q
        result = search_and_get_reviews(q)
        if not result: return []
        return [{
            "id": result.get("name"),
            "place_name": result.get("name"),
            "name": result.get("name"),
            "address_name": result.get("address"),
            "address": result.get("address"),
            "place_url": result.get("name"),
            "category_name": "식당"
        }]
    except: return []

# 💡 [방어] 한 번에 최대 2개의 크롤러만 동작
crawler_semaphore = threading.Semaphore(2)

# 구글 상호: 괄호·| 뒤 **부가 설명** / 영·중·일 꼬리 (상호 **본문 한글**은 잘랄 때 주의)
_TRAILING_PAREN = re.compile(
    r"[\(（\[\{【［\uFF08][^\)\]）\]\}】］\uFF09]{0,80}[\)\]）\]\}】］\uFF09]\s*"
)
_TRAILING_LATIN = re.compile(
    r"[\s\-_/]*[A-Za-z][A-Za-z0-9'&\.\-]{0,50}(?:\s+[A-Za-z0-9'&\.\-]{0,30})*[/／]?"
)
_TRAILING_CJK_FOREIGN = re.compile(
    r"[\s\-_/·]*[一-龥ぁ-んァ-ヶ㐀-㿯々〆〇]{1,40}$"
)


def clean_place_name(name: str) -> str:
    """
    **검색·프롬프트용 핵심 키워드** 추출. 상호 **단어(토큰)를 함부로 삭제하지 않는다.**
    '존맛식당' → '존맛'이 포함된 형태로 유지 (| 뒤 꼬리·영어 설명만 제거).
    """
    if not name or not str(name).strip():
        return ""
    s = str(name).strip()
    s = s.replace("｜", "|")
    if "|" in s:
        s = s.split("|", 1)[0].strip()

    for _ in range(4):
        t = _TRAILING_PAREN.sub(" ", s)
        if t == s:
            break
        s = t

    s = re.sub(r"\s+", " ", s).strip()

    for _ in range(3):
        before = s
        s2 = re.sub(
            r"([가-힣0-9]+)\s+([A-Za-z][A-Za-z0-9'&\.\-\s,]{0,50})$",
            r"\1",
            s,
        )
        s2 = _TRAILING_LATIN.sub("", s2).strip()
        s2 = re.sub(r"[\-–—_/\s]+$", "", s2)
        s2 = re.sub(r"\s+", " ", s2).strip()
        s = s2
        if s == before:
            break

    s3 = re.sub(
        r"([가-힣0-9]+)\s*([一-龥㐀-㿯ぁ-んァ-ヶ・]{1,20})$",
        r"\1",
        s,
    )
    s = _TRAILING_CJK_FOREIGN.sub("", s3).strip() if s3 else ""
    s = s.strip("·•.,，、 ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def korean_hangul_keywords_only(s: str) -> str:
    """영어·특수문자 제거 후 순수 한글(·숫자 제외) 토큰만 — 3차 검색용."""
    s = re.sub(r"[^가-힣]+", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def take_head_name_words_2_3(name_core: str) -> str:
    """2~3단어(공백 기준). '존맛식당'은 한 토큰이면 그대로 1어절로 사용."""
    toks = [t for t in re.split(r"\s+", (name_core or "").strip()) if t]
    if not toks:
        return ""
    if len(toks) == 1:
        return toks[0]
    n = 3 if len(toks) >= 3 else 2
    return " ".join(toks[:n])


def extract_dong_gu_from_address(address: str) -> tuple[str, str]:
    """
    Google/Kakao 주소 문자열에서 '○○구'·'○○동' 추출. 없으면 ("", "").
    """
    if not address or not str(address).strip():
        return ("", "")

    s = re.sub(r"\s+", " ", str(address).strip())
    s = re.sub(
        r"(?i)대한민국|republic of korea|south korea|korea,?\s*rep\.?|kr\b|korea|서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|제주특별자치도|경기도|강원특별자치도|충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도",
        " ",
        s,
    )
    s = re.sub(r"\s+", " ", s).strip()

    gu = ""
    dong = ""
    m = re.search(r"([가-힣]{1,5}구)\s+([가-힣0-9·]{0,4})([가-힣]{1,5}동)\b", s)
    if m:
        gu, dong = m.group(1), m.group(3)
    if not dong:
        dlist = re.findall(r"[가-힣0-9]{0,2}[가-힣]{1,4}동(?![가-힣])", s)
        if dlist:
            dong = dlist[-1]
    if not gu and dong:
        pre = s[: s.find(dong)]
        m_gu = re.findall(r"([가-힣]{1,5}구)", pre)
        if m_gu:
            gu = m_gu[-1]

    return (gu, dong)


def extract_sido_gu_dong_for_log(address: str) -> dict[str, str]:
    s = re.sub(r"\s+", " ", (address or "").strip())
    gugun, dong = extract_dong_gu_from_address(address)
    sido = ""
    m = re.search(
        r"(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|"
        r"세종특별자치시|제주특별자치도|경기도|강원특별자치도|"
        r"충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"[가-힣]+광역시)",
        s,
    )
    if m:
        sido = m.group(1)
    return {"sido": sido, "gugun": gugun, "dong": dong}


def _normalize_kakao_q(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _iter_kakao_flexible_plans(
    name_raw: str, address: str
) -> list[tuple[str, str, str]]:
    """
    (라벨, API전체쿼리, 로그용: 동+키워드) 1~3차. 동일 쿼리는 생략.
    1차: 구글 상호 **전문** (정확 일치·긴 광고명 대비)
    2차: **동** + `clean` 상호 **앞 2~3어절** (성공률에 유리)
    3차: **동** + **순수 한글** (영·기호 제거)
    """
    nr = (name_raw or "").strip()
    if not nr:
        return []
    _gu, dong = extract_dong_gu_from_address(address)
    core = clean_place_name(nr) or nr
    head2 = take_head_name_words_2_3(core)
    hang = korean_hangul_keywords_only(nr) or korean_hangul_keywords_only(core)

    # 1차: 전문
    q1 = nr
    log1 = f"전문: {nr[:50]}{'…' if len(nr) > 50 else ''}"

    # 2차: 동 + 앞 2~3어절(핵심 키워드, 존맛·맛집 토큰 보존)
    q2 = f"{dong} {head2}".strip() if (dong and head2) else (head2 or core)
    log2 = f"{dong or '(동없음)'} + {head2}" if head2 else "(어절없음)"

    # 3차: 동 + 순수 한글
    q3 = f"{dong} {hang}".strip() if (dong and hang) else (hang or "")
    if not q3 and dong:
        q3 = dong.strip()
    log3 = f"{dong or '(동없음)'} + {hang}" if hang else f"{dong or ''}"

    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for label, q, log_kw in (("1차", q1, log1), ("2차", q2, log2), ("3차", q3, log3)):
        nq = _normalize_kakao_q(q)
        if not nq or nq in seen:
            continue
        seen.add(nq)
        out.append((label, nq, log_kw))
    return out


def run_kakao_advanced_analysis(query: str, place_name_raw: str, address: str, lang: str):
    name_clean = clean_place_name(place_name_raw)
    reg = extract_sido_gu_dong_for_log(address)
    print(
        f"🧹 [카카오] 상호(원문)='{place_name_raw}' | 핵심키워드(clean)='{name_clean}'\n"
        f"   🗺️ [시/구/동] 시={reg['sido'] or '—'} | 구={reg['gugun'] or '—'} | 동={reg['dong'] or '—'} | "
        f"address(80자)='{(address or '')[:80]}'"
    )
    search_plans = _iter_kakao_flexible_plans(place_name_raw, address)
    if not search_plans:
        print("🚨 [크롤러 중단] 검색 키워드가 비어 있음")
        if collection is not None:
            collection.update_one(
                {"name": query},
                {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}},
            )
        return

    print(
        f"🚦 [크롤러 대기열] {len(search_plans)}단계(주소교차검증·후보도) | "
        + " | ".join(f"{l}→「{k[:40]}{'…' if len(k) > 40 else ''}」" for l, k, _ in search_plans)
    )

    with crawler_semaphore:
        time.sleep(random.uniform(1, 3))

        kakao_query = ""
        place_id = None
        try:
            for label, kq, kw_log in search_plans:
                print(
                    f"카카오 검색 시도: {label} [동+추출키워드: {kw_log}] | 전체쿼리: {kq}"
                )
                place_id = get_kakao_place_id(kq, address)
                if place_id:
                    kakao_query = kq
                    print(
                        f"✅ {label} 검색·주소교차로 place_id 확보 (이후 리뷰·분석에 사용)"
                    )
                    break
                print(f"   … {label} API 결과 없음·다음 전략")

            if not place_id:
                print(
                    f"🚨 [크롤러 중단] 1~3차 모두 실패. clean='{name_clean}' / 주소='{(address or '')[:100]}…'"
                )
                if collection is not None:
                    collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}})
                return

            print(f"🏃‍♂️ [크롤러] 리뷰 수집: 성공 키워드='{kakao_query}'")
            reviews = get_deep_kakao_reviews(place_id)
            if len(reviews) < 5: 
                print(
                    f"🚨 [크롤러 중단] 키워드='{kakao_query}' 카카오 리뷰 부족 ({len(reviews)}개)"
                )
                if collection is not None:
                    collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}})
                return

            prompt = get_deep_prompt(lang, name_clean or kakao_query, reviews)
            response = client.chat.completions.create(
                model="gpt-4o-mini", response_format={ "type": "json_object" },
                messages=[{"role": "system", "content": "You are a JSON generating assistant."}, {"role": "user", "content": prompt}]
            )
            ai_data = json.loads(response.choices[0].message.content)
            try:
                kakao_score = float(ai_data.get("realScore", 0) or 0)
            except (TypeError, ValueError):
                kakao_score = 0.0

            if collection is not None:
                set_payload = {f"kakao_result_{lang}": ai_data}
                if kakao_score >= 3.5:
                    set_payload["map_flag"] = {
                        "name": name_clean or kakao_query,
                        "romanizedName": (ai_data.get("romanizedName") or "").strip(),
                        "address": address,
                        "realScore": kakao_score,
                        "isTrophy": kakao_score >= 4.0,
                        "source": "kakao",
                        "aiSummary": ai_data.get("aiSummary", ""),
                        "details": ai_data.get("details"),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                    }
                collection.update_one({"name": query}, {"$set": set_payload})
                print(
                    f"🔥 [크롤러 완료] API검색='{kakao_query}' (정제='{name_clean}') 고급 분석 DB 저장 완료!"
                )
                if kakao_score >= 3.5:
                    trophy = "황금 트로피" if kakao_score >= 4.0 else "검증 깃발"
                    print(
                        f"🚩 [깃발] API검색='{kakao_query}' 카카오 점수 {kakao_score:.1f} → map_flag ({trophy})"
                    )
                
        except Exception as e:
            print(
                f"🚨 [크롤러 예외] query={query!r} API검색='{kakao_query}' (정제='{name_clean}'): {e}"
            )
            if collection is not None:
                collection.update_one(
                    {"name": query},
                    {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}},
                )

@app.post("/api/analyze")
async def analyze_place(request: Request, background_tasks: BackgroundTasks):
    global last_queries
    client_ip = request.client.host
    try: data = await request.json()
    except: data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    if query: query = query[:100]
    
    address = data.get("address", "") 
    lang = data.get("lang") or "ko"
    
    if collection is not None:
        cached_item = collection.find_one({"name": query})
        if cached_item:
            realtime_cache_key = f"result_{lang}"
            kakao_cache_key = f"kakao_result_{lang}"
            
            if realtime_cache_key in cached_item and cached_item[realtime_cache_key]:
                cache_date = datetime.strptime(cached_item["date"], "%Y-%m-%d")
                if datetime.now() - cache_date < timedelta(days=30):
                    result_data = cached_item[realtime_cache_key]
                    result_data["isNewDiscovery"] = False 
                    
                    if kakao_cache_key in cached_item:
                        status = cached_item[kakao_cache_key].get("status")
                        if status == "processing" or status == "no_data":
                            result_data["has_advanced"] = False
                        else:
                            result_data["has_advanced"] = True
                            result_data["kakao_data"] = cached_item[kakao_cache_key]
                    else:
                        result_data["has_advanced"] = False
                        collection.update_one({"name": query}, {"$set": {kakao_cache_key: {"status": "processing"}}}, upsert=True)
                        
                        background_tasks.add_task(
                            run_kakao_advanced_analysis, query, result_data["name"], address, lang
                        )

                    kd = result_data.get("kakao_data") if isinstance(result_data.get("kakao_data"), dict) else None
                    text_parts = [
                        result_data.get("aiSummary") or "",
                        result_data.get("name") or "",
                        query or "",
                    ]
                    score_fb = float(result_data.get("realScore") or 0)
                    det_fb = dict(result_data.get("details") or {})
                    if kd:
                        text_parts.append(kd.get("aiSummary") or "")
                        score_fb = float(kd.get("realScore") or score_fb)
                        if kd.get("details"):
                            det_fb = dict(kd.get("details") or {})
                    attach_tags_and_plan_b(
                        result_data,
                        lang,
                        text_parts,
                        score_fb,
                        det_fb,
                        (result_data.get("name") or query or ""),
                    )

                    return result_data

    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404)

    if not analyze_rate_limit_allows(client_ip):
        raise HTTPException(
            status_code=429,
            detail="하루 검색 횟수를 모두 사용하셨습니다! 내일 다시 찾아주세요. 🚀",
        )

    try:
        prompt = get_fast_prompt(lang, place_info)
        response = client.chat.completions.create(
            model="gpt-4o-mini", response_format={ "type": "json_object" },
            messages=[{"role": "system", "content": "You are a JSON generating assistant."}, {"role": "user", "content": prompt}]
        )
        ai_data = json.loads(response.choices[0].message.content)
        
        final_result = {
            **ai_data, "name": ai_data.get("translatedName") or place_info['name'], 
            "address": ai_data.get("translatedAddress") or place_info['address'], 
            "rating": place_info['rating'], "isNewDiscovery": True, "has_advanced": False
        }

        attach_tags_and_plan_b(
            final_result,
            lang,
            [" ".join(place_info["reviews"]), place_info["name"], query],
            float(ai_data.get("realScore") or 0),
            ai_data.get("details"),
            final_result["name"],
        )
        
        if collection is not None:
            update_data = {
                "name": query, 
                "date": datetime.now().strftime("%Y-%m-%d"), 
                f"result_{lang}": final_result,
                f"kakao_result_{lang}": {"status": "processing"} 
            }
            collection.update_one({"name": query}, {"$set": update_data}, upsert=True)
        
        background_tasks.add_task(
            run_kakao_advanced_analysis, query, place_info["name"], address, lang
        )

        record_chargeable_analyze(client_ip)
        
        return final_result

    except Exception as e:
        raise HTTPException(status_code=500, detail="분석 실패")

@app.post("/api/map-flags")
def save_map_flag_disabled():
    """구 프론트(구글 점수 기반)용 엔드포인트. 깃발은 카카오 심층 분석 완료 시 서버가 저장합니다."""
    raise HTTPException(
        status_code=410,
        detail="Map flags are now persisted from Kakao deep analysis; client POST is no longer supported.",
    )

@app.get("/api/map-flags")
def get_map_flags():
    if collection is None:
        return []

    flags = []
    try:
        docs = collection.find(
            {
                "map_flag": {"$exists": True, "$ne": None},
                "map_flag.realScore": {"$gte": 3.5},
            }
        )

        for doc in docs:
            mf = doc.get("map_flag") or {}
            name = mf.get("name") or doc.get("name", "")
            address = mf.get("address") or doc.get("address", "")
            score = mf.get("realScore", 0)
            try:
                score = float(score)
            except (TypeError, ValueError):
                score = 0.0
            if score < 3.5:
                continue
            is_trophy = bool(mf.get("isTrophy", score >= 4.0))
            translated_name = (mf.get("translatedName") or "").strip()
            if not translated_name:
                for res_key in ("result_en", "result_ko"):
                    r = doc.get(res_key) or {}
                    translated_name = (r.get("translatedName") or "").strip()
                    if translated_name:
                        break
            flags.append(
                {
                    "name": name,
                    "romanizedName": (mf.get("romanizedName") or "").strip(),
                    "translatedName": translated_name,
                    "address": address,
                    "score": score,
                    "isTrophy": is_trophy,
                    "source": mf.get("source", "kakao"),
                    "aiSummary": mf.get("aiSummary", ""),
                    "details": mf.get("details"),
                }
            )
        return flags
    except Exception as e:
        print("🚨 깃발 불러오기 에러:", e)
        return []
   
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))