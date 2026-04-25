import os
import json
import time
import re
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    if lang == "en":
        instruction = (
            "You are a 'Chief Culinary Profiler' analyzing 25 raw reviews. Base score is 2.5. "
            "details.taste and details.value MUST be JSON float numbers 1.0-5.0, never 0, inferred from context."
        )
        guidelines = """
        [Deep Analysis Logic]
        1. Profiling: Prioritize detailed reviews over simple praise.
        2. Strict 'Fatal Flaw': Only [Hygiene issues, Extreme Rudeness, Spoiled Food] significantly lower the score. 
        3. Reference Info: Price, waiting, and parking issues must be mentioned in the summary for user reference, but they are NOT fatal flaws that crush the score.
        4. NO USERNAMES: Absolutely no mention of reviewer nicknames or IDs.
        5. Practical Tip: Extract one actionable tip.

        [MANDATORY — Context inference; details.taste and details.value MUST never be 0.0]
        - Infer from CONTEXT, not from searching for the words "taste" or "value." For restaurant reviews, taste and value are always inferable in the 1.0–5.0 range.
        - TASTE: salty, sweet, tough, fresh, delicious, texture, flavor, "amazing food", "bad food", "would come back for the food"—all map to taste. Never 0.0. Never a string; output a JSON number float.
        - VALUE: expensive, cheap, small portions, worth it, "generous for the price", "rip-off", value for money—all map to value. Never 0.0. Float only.
        - If any detail dimension has almost no signal (e.g. wait time never mentioned), use 3.0 for THAT dimension as neutral default—never 0.0. Taste and value in particular: forbidden to output 0.0; infer from the whole text if needed.
        - realScore: number 1.0–5.0. eventProbability: integer. details.*: all numeric floats, e.g. 4.5, not "4.5" strings.
        """
        json_format = (
            '{ "realScore": 3.8, "eventProbability": 20, "aiSummary": "…", "details": { '
            '"taste": 4.2, "value": 3.6, "service": 3.0, "time": 3.0, "hygiene": 3.0 } }  '
            "(All details values are JSON float numbers; taste and value: 1.0-5.0, NEVER 0.0; strings are forbidden for scores.)"
        )
    else:
        instruction = (
            "당신은 25개의 카카오 리뷰를 해부하는 '전문 미식 프로파일러'입니다. 기준점은 2.5점입니다. "
            "taste, value는 문맥에서 반드시 1.0~5.0 **실수(JSON number)**; 0.0 출력은 오류이며 절대 금지."
        )
        guidelines = """
        [💡 전문 분석가 감지 논리]
        1. 리뷰어 분석: 깐깐한 리뷰어의 구체적인 평가를 중심으로 신뢰도를 파악하세요.
        2. 치명적 결함(감점 기준): [위생 불량, 심각한 불친절, 상한 음식]이 발견될 때만 점수를 대폭 삭감합니다.
        3. 필수 참고 정보(요약 반영): 가격이 비싸거나 웨이팅이 길거나 주차가 힘든 점은 '치명적 단점'이 아니므로 점수를 파괴하는 근거로 쓰지 마세요. 하지만 방문객이 꼭 알아야 할 정보이므로 요약문(심층 분석 문단)에 반드시 '참고할 내용'으로 언급하세요.
        4. 닉네임 언급 절대 금지: 리뷰어의 닉네임(예: '골드', '은별' 등)을 절대 요약에 넣지 마세요. '일부 리뷰어', '방문자' 등으로 지칭하세요.
        5. 실전 꿀팁: 주차, 예약, 추천 메뉴 등 실질적인 팁 한 줄.

        [필수 — 문맥 추론; details의 taste·value는 0.0 절대 금지, Float만]
        - "맛" "가성비" 단어가 없어도 **전체 문맥**에서 추론한다. 키워드 매칭으로 점수를 0이나 누락시키지 말 것.
        - taste: '짜다, 달다, 질기다, 쫄깃, 신선, 비린, 존맛, JMT, 입이 즐겁' 등 **음·식·질** 관련 언급→ 반드시 1.0~5.0 실수.
        - value: '비싸, 싸, 양 적, 혜자, 돈 아깝, 가성비, 푸짐' 등 **가격·양** 관련 → 1.0~5.0, 0.0 **출력 금지**.
        - 식당 리뷰에서 taste·value 둘 다 0.0이 되는 것은 **논리적 불가**. 언급이 약하면 **전체 톤**으로 추정. **0.0 대신 1.0~5.0**만 사용.
        - time·service·hygiene 등 **그 축**에 대한 언급이 사실상 없을 때만 3.0 **기본값** (0.0이 아님). taste·value는 기본 3.0는 최후 수단(정보가 거의 없을 때)이고, **여전히 0.0은 쓰지 말 것**.
        - JSON: realScore, details의 모든 점수는 **숫자(실수)**. 예: "taste": 4.3 — **문자열 "4.3"이나 0는 금지.**
        """
        json_format = (
            '{ "realScore": 3.7, "eventProbability": 15, "aiSummary": "첫 문단은 🔍 [심층 분석]으로, 둘째는 💡 [실전 꿀팁]으로 시작하는 두 문단", "details": { '
            '"taste": 4.1, "value": 3.8, "service": 3.0, "time": 3.0, "hygiene": 3.0 } }  '
            "(taste, value, service, time, hygiene: 각각 1.0~5.0 **JSON number**; taste·value=0.0 **절대 금지**.)"
        )
    
    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nTarget: {place_name}\nReviews: {reviews_text}"

app = FastAPI()

@app.middleware("http")
async def limit_requests(request: Request, call_next):
    if request.url.path == "/api/analyze":
        client_ip = request.client.host
        now = time.time()
        user_requests[client_ip] = [t for t in user_requests[client_ip] if now - t < WINDOW_SECONDS]
        
        if len(user_requests[client_ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429, 
                content={"detail": "하루 검색 횟수를 모두 사용하셨습니다! 내일 다시 찾아주세요. 🚀"}
            )
        user_requests[client_ip].append(now)
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
                        
                    return result_data

    place_info = search_and_get_reviews(query)
    if not place_info: raise HTTPException(status_code=404)
    
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
            flags.append(
                {
                    "name": name,
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