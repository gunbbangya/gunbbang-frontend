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
        instruction = "You are a 'First-Line Fake Review Detector'. Base score is 2.5."
        guidelines = """
        [Detection & Scoring Logic]
        1. Pattern Recognition: If keywords or hashtags repeat unnaturally, increase 'eventProbability'.
        2. Strict 'Fatal Flaw' (Score Eraser): Only [Poor Hygiene (bugs, hair), Extreme Rudeness (insults, ignoring customers), Spoiled Food] are fatal. Slash the score only for these.
        3. Reference Info (Include in Summary): Expensive prices, long waiting times, and parking issues are NOT fatal flaws. Do NOT slash scores for these, but ALWAYS mention them in the summary as 'reference info' so users can be prepared.
        4. NO USERNAMES: Never mention specific nicknames or usernames found in reviews. Use generic terms like 'some visitors'.
        """
        json_format = '{ "translatedName": "Name", "translatedAddress": "Address", "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "Summary including patterns, fatal flaws, and reference info (price/wait/parking). No nicknames.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    else:
        instruction = "당신은 5개의 리뷰에서 조작 패턴을 찾아내는 '1차 필터링 요원'입니다. 기준점은 2.5점입니다."
        guidelines = """
        [🔍 1차 방어선 감지 및 채점 논리]
        1. 앵무새 패턴 감지: 특정 키워드나 해시태그가 반복되면 조작 확률(eventProbability)을 높이세요.
        2. 치명적 결함(점수 감점 기준): 오직 [위생 불량(벌레, 이물질), 심각한 불친절(욕설, 반말, 손님 무시), 상한 음식]만 치명적 결함으로 간주하여 점수를 대폭 낮춥니다.
        3. 필수 참고 정보(요약 포함): 비싼 가격, 긴 웨이팅, 주차 불편은 '치명적 결함'이 아닙니다. 이를 이유로 점수를 대폭 깎지 마세요. 대신, 사용자가 참고할 수 있도록 요약문에 반드시 해당 내용(가격/웨이팅/주차 등)을 포함하여 서술하세요.
        4. 닉네임 언급 금지: 리뷰어의 닉네임이나 실명을 절대 직접 언급하지 마세요. '방문객들', '실사용자' 등의 표현을 사용하세요.
        """
        json_format = '{ "translatedName": "가게 이름", "translatedAddress": "가게 주소", "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "조작 정황, 치명적 단점, 그리고 참고 정보(가격/웨이팅/주차)를 포함하여 1~2줄로 요약하세요. 닉네임 언급은 금지합니다.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    
    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nInput Data: Name: {place_info['name']}\nReviews: {' '.join(place_info['reviews'])}"

def get_deep_prompt(lang, place_name, reviews):
    reviews_text = "\n".join(reviews)
    if lang == "en":
        instruction = "You are a 'Chief Culinary Profiler' analyzing 25 raw reviews. Base score is 2.5."
        guidelines = """
        [Deep Analysis Logic]
        1. Profiling: Prioritize detailed reviews over simple praise.
        2. Strict 'Fatal Flaw': Only [Hygiene issues, Extreme Rudeness, Spoiled Food] significantly lower the score. 
        3. Reference Info: Price, waiting, and parking issues must be mentioned in the summary for user reference, but they are NOT fatal flaws that crush the score.
        4. NO USERNAMES: Absolutely no mention of reviewer nicknames or IDs.
        5. Practical Tip: Extract one actionable tip.
        """
        json_format = '{ "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "Para 1 (🔍 [Analysis]): Deep dive into flaws and reference info (price/wait/parking) without using nicknames. Para 2 (💡 [Visitor Tip]): One practical tip.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    else:
        instruction = "당신은 25개의 카카오 리뷰를 해부하는 '전문 미식 프로파일러'입니다. 기준점은 2.5점입니다."
        guidelines = """
        [💡 전문 분석가 감지 논리]
        1. 리뷰어 분석: 깐깐한 리뷰어의 구체적인 평가를 중심으로 신뢰도를 파악하세요.
        2. 치명적 결함(감점 기준): [위생 불량, 심각한 불친절, 상한 음식]이 발견될 때만 점수를 대폭 삭감합니다.
        3. 필수 참고 정보(요약 반영): 가격이 비싸거나 웨이팅이 길거나 주차가 힘든 점은 '치명적 단점'이 아니므로 점수를 파괴하는 근거로 쓰지 마세요. 하지만 방문객이 꼭 알아야 할 정보이므로 요약문(심층 분석 문단)에 반드시 '참고할 내용'으로 언급하세요.
        4. 닉네임 언급 절대 금지: 리뷰어의 닉네임(예: '골드', '은별' 등)을 절대 요약에 넣지 마세요. '일부 리뷰어', '방문자' 등으로 지칭하세요.
        5. 실전 꿀팁: 주차, 예약, 추천 메뉴 등 실질적인 팁 한 줄.
        """
        json_format = '{ "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "두 문단 작성. 첫 문단은 \'🔍 [심층 분석]\'으로 시작하여 결함 및 참고 정보(가격/웨이팅/주차)를 닉네임 없이 서술. 두 번째 문단은 줄바꿈 후 \'💡 [실전 꿀팁]\'으로 시작.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    
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

def run_kakao_advanced_analysis(query: str, search_keyword: str, address: str, lang: str):
    print(f"🚦 [크롤러 대기열] '{search_keyword}' 순서 대기 중...")
    
    with crawler_semaphore:
        time.sleep(random.uniform(1, 3))
        print(f"🏃‍♂️ [크롤러 출동] '{search_keyword}' 분석 시작!")
        
        try:
            place_id = get_kakao_place_id(search_keyword, address)
            if not place_id: 
                print(f"🚨 [크롤러 중단] 카카오맵에서 '{search_keyword}' 못 찾음")
                if collection is not None:
                    collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}})
                return

            reviews = get_deep_kakao_reviews(place_id)
            if len(reviews) < 5: 
                print(f"🚨 [크롤러 중단] '{search_keyword}' 카카오 리뷰 부족 ({len(reviews)}개)")
                if collection is not None:
                    collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}})
                return

            prompt = get_deep_prompt(lang, search_keyword, reviews)
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
                        "name": search_keyword,
                        "address": address,
                        "realScore": kakao_score,
                        "isTrophy": kakao_score >= 4.0,
                        "source": "kakao",
                        "aiSummary": ai_data.get("aiSummary", ""),
                        "details": ai_data.get("details"),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                    }
                collection.update_one({"name": query}, {"$set": set_payload})
                print(f"🔥 [크롤러 완료] '{search_keyword}' 고급 분석 DB 저장 완료!")
                if kakao_score >= 3.5:
                    trophy = "황금 트로피" if kakao_score >= 4.0 else "검증 깃발"
                    print(f"🚩 [깃발] 카카오 점수 {kakao_score:.1f} → 지도용 map_flag 저장 ({trophy})")
                
        except Exception as e:
            if collection is not None:
                collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": {"status": "no_data"}}})

def clean_place_name(name):
    # | ( [ - – 같은 구분 기호가 나오면 그 앞부분만 취함
    cleaned = re.split(r'[|(\[–-]', name)[0].strip()
    return cleaned

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
                        
                        kakao_keyword = clean_place_name(result_data["name"])
                        background_tasks.add_task(run_kakao_advanced_analysis, query, kakao_keyword, address, lang)
                        
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
        
        kakao_keyword = clean_place_name(place_info['name'])
        background_tasks.add_task(run_kakao_advanced_analysis, query, kakao_keyword, address, lang)
        
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