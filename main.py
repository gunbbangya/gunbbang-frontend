import os
import json
import re
import time  # 💡 추가됨
from collections import defaultdict  # 💡 추가됨
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse # 💡 추가됨
from scraper import search_and_get_reviews 
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"
last_queries = {} 

# --- Rate Limit 설정 ---
user_requests = defaultdict(list)
RATE_LIMIT = 10 
WINDOW_SECONDS = 60

def get_dynamic_prompt(lang, place_info):
    if lang == "en":
        # 영어 모드: 비평가 정체성 강화
        instruction = "You are a 'Cold-blooded Global Restaurant Critic'. Be extremely skeptical and strict with scores."
        guidelines = """
        [Strict Scoring Rules]
        1. Base Score: Start from 3.0. Do not give 4.5+ unless it's truly flawless.
        2. Strict Deductions: 
           - Rude service or Hygiene issues: -1.5 points immediately.
           - Overpriced or Long wait: -1.0 point.
        3. Hard Ceiling: If the 'aiSummary' mentions ANY critical negatives (service, hygiene, bait-and-switch), 'realScore' MUST NOT exceed 3.5.
        4. Consistency: If your summary is critical, the 'details' scores must be low. No "Great food but 1 star" or "Bad food but 5 stars".
        5. Translation: Translate 'Name' and 'Address' into English.
        """
        json_format = """
        {
            "translatedName": "English Name",
            "translatedAddress": "English Address",
            "realScore": 1.0~5.0,
            "aiSummary": "Critical summary",
            "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" }
        }
        """
    else:
        # 한국어 모드: '까칠한 프로파일러' 주입
        instruction = "당신은 식당의 광고성 리뷰를 걸러내고 단점을 집요하게 파헤치는 '냉혹한 미식 비평가'입니다."
        guidelines = """
        [엄격한 채점 기준]
        1. 기본 점수: 3.0점에서 시작하세요. 4.0점 이상은 대한민국 상위 1% 식당에만 부여합니다.
        2. 감점 지침: 
           - '불친절', '위생 문제', '바가지' 언급 시 무조건 해당 항목 1~2점 및 총점 -1.5점 감점.
           - '웨이팅 너무 김', '비쌈' 언급 시 -1.0점 감점.
        3. 점수 상한선: 요약문에 부정적인 팩트(불친절, 위생, 맛의 기복 등)가 포함되어 있다면 'realScore'는 절대로 3.5점을 넘길 수 없습니다.
        4. 일관성: 요약문에서 욕을 했다면 점수도 낮아야 합니다. 유저가 '글은 나쁜데 점수는 왜 높지?'라고 의심하지 않게 하세요.
        """
        json_format = """
        {
            "translatedName": "가게 이름",
            "translatedAddress": "가게 주소",
            "realScore": 1.0~5.0,
            "aiSummary": "냉정한 요약",
            "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" }
        }
        """

    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nInput Data: Name: {place_info['name']}, Address: {place_info['address']}\nReviews: {' '.join(place_info['reviews'])}"
    
app = FastAPI()

# --- 미들웨어: Rate Limit ---
@app.middleware("http")
async def limit_requests(request: Request, call_next):
    if request.url.path == "/api/analyze":
        client_ip = request.client.host
        now = time.time()
        user_requests[client_ip] = [t for t in user_requests[client_ip] if now - t < WINDOW_SECONDS]
        
        if len(user_requests[client_ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429, 
                content={"detail": "Too many requests. AI도 숨 좀 돌려야 해요! 1분 뒤에 다시 해주세요. 🚀"}
            )
        user_requests[client_ip].append(now)
    return await call_next(request)

# --- 미들웨어: CORS ---
ALLOWED_ORIGINS = [
    "https://gunbbang-frontend.vercel.app", 
    "http://localhost:3000",                
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_cache():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(cache_data, f, ensure_ascii=False, indent=4)

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

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    try:
        data = await request.json()
    except: data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    
    # 💡 [보안] 100자 제한 로직의 올바른 위치
    if query:
        query = query[:100]
        
    lang = data.get("lang") or "ko"
    cache = load_cache()
    cache_key = f"{query}_{lang}"
    
    if cache_key in cache:
        cached_item = cache[cache_key]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info: raise HTTPException(status_code=404)

    target_models = ['models/gemini-2.5-flash', 'models/gemini-2.0-flash', 'models/gemini-flash-latest']
    
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = get_dynamic_prompt(lang, place_info)
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group())
                final_result = {
                    **ai_data, 
                    "name": ai_data.get("translatedName") or place_info['name'], 
                    "address": ai_data.get("translatedAddress") or place_info['address'], 
                    "rating": place_info['rating']
                }
                cache[cache_key] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
                save_cache(cache)
                return final_result
        except: continue
    raise HTTPException(status_code=500, detail="분석 실패")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
