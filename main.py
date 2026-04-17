import os
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scraper import search_and_get_reviews 
import google.generativeai as genai
from dotenv import load_dotenv
from pymongo import MongoClient  # 💡 MongoDB 도구
import certifi


load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# 💡 MongoDB 클라우드 연결 설정
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["jjin_view_db"]
    collection = db["places_cache"]
    print("✅ MongoDB 클라우드 연결 성공!")
except Exception as e:
    print(f"🚨 MongoDB 연결 실패 (URI를 확인하세요): {e}")
    collection = None

last_queries = {} 

# --- Rate Limit 설정 ---
user_requests = defaultdict(list)
RATE_LIMIT = 10 
WINDOW_SECONDS = 60

# --- 동적 프롬프트 생성 (구글 데이터 맞춤형 - 리뷰어 성향 삭제) ---
def get_dynamic_prompt(lang, place_info):
    if lang == "en":
        instruction = "You are a 'Cold-blooded Global Restaurant Critic'. Expose fake reviews, but NEVER explicitly mention your detection process or keywords like 'event'. Write the summary naturally and professionally, like a Michelin guide critique."
        guidelines = """
        [Detection: Review Events & Fake Patterns]
        1. Identify phrases like "got a free drink/side", "event participation", "review for service".
        2. Contextual Detection: Even without 'event' keywords, if a 5-star review only praises "kindness" or "cleanliness" without any specific details about the food (taste, texture, ingredients), treat it as a high-probability fake/promotional pattern.
        3. Suspicious 5.0 stars: Extremely short reviews or emoji-only reviews are considered zero-value data.
        4. Weighting: Give 2x weight to 1~3 star reviews that describe specific issues (hygiene, attitude, price).
        5. Calculate 'eventProbability' (0~100%): High probability if reviews lack substance or focus solely on non-food factors.
        
        [Strict Scoring Rules]
        1. Base Score: 3.0. Do not exceed 4.0 unless it's a legendary spot.
        2. Deductions: Rude service/Hygiene (-1.5), Overpriced (-1.0).
        3. Hard Ceiling: If 'eventProbability' > 70%, the 'realScore' MUST NOT exceed 2.9 regardless of other factors.
        """
        json_format = """
        {
            "translatedName": "English Name",
            "translatedAddress": "English Address",
            "realScore": 1.0~5.0,
            "eventProbability": 0~100,
            "aiSummary": "Critical summary focusing on fake patterns and food quality",
            "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" }
        }
        """
    else:
        instruction = "당신은 광고성 리뷰를 걸러내고 조작된 평점을 파괴하는 '냉혹한 미식 프로파일러'입니다. 단, 요약 시 '이벤트 키워드가 감지되지 않았다' 같은 기계적인 분석 과정은 절대 언급하지 말고, 미슐랭 평론가처럼 자연스럽고 세련되게 결론만 작성하세요."
        guidelines = """
        [리뷰 이벤트 및 조작 패턴 감지]
        1. 핵심 키워드 감시: '서비스 받았어요', '이벤트 참여', '음료수 서비스', '사진 리뷰 약속' 등의 문구가 보이면 무조건 'eventProbability'를 높이세요.
        2. 맥락적 정황 포착: '이벤트'라는 직접적 단어가 없더라도, 음식(맛, 식감, 양)에 대한 구체적 묘사 없이 "사장님이 친절해요", "가게가 예뻐요" 등 부차적인 칭찬만 나열된 5점 리뷰는 보상형 리뷰일 확률이 매우 높으므로 'eventProbability'에 적극 반영하세요.
        3. 영혼 없는 5점: "맛있어요", "최고예요" 등 구체적인 설명 없이 이모티콘만 있거나 너무 짧은 5점 리뷰는 '리뷰 이벤트' 정황으로 간주합니다.
        4. 신뢰도 가중치: 사진이 없거나 짧은 5점보다, 단점을 구체적으로 지적한 1~3점 리뷰에 2배의 가중치를 두어 점수를 깎으세요.
        5. 'eventProbability' 산출: 0~100% 사이의 정수로, 리뷰 이벤트가 의심되는 정도를 계산하세요.

        [엄격한 채점 기준]
        1. 기본 점수: 3.0점. 4.0점 이상은 대한민국 상위 1% 식당에만 부여합니다.
        2. 점수 상한선: 'eventProbability'가 70% 이상이면 'realScore'는 무조건 2.9점 이하로 강제 고정합니다.
        3. 감점: 불친절/위생(-1.5점), 웨이팅/비쌈(-1.0점).
        """
        json_format = """
        {
            "translatedName": "가게 이름",
            "translatedAddress": "가게 주소",
            "realScore": 1.0~5.0,
            "eventProbability": 0~100,
            "aiSummary": "리뷰 이벤트 정황을 포함한 냉정한 분석",
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

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    try:
        data = await request.json()
    except: data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    if query:
        query = query[:100]
        
    lang = data.get("lang") or "ko"
    
    # 💡 [포인트 1] 이 식당이 예전에 한 번이라도 검색된 적 있는지 기억해두기!
    already_existed = False 
    
    if collection is not None:
        cached_item = collection.find_one({"name": query})
        
        if cached_item:
            already_existed = True # DB에 흔적이 있으니 최초 발견은 아님!
            
            # 1. 수집 공장(db_builder)이 모아둔 데이터
            builder_cache_key = f"analysis_{lang}"
            if builder_cache_key in cached_item and cached_item[builder_cache_key]:
                return {
                    **cached_item[builder_cache_key],
                    "name": cached_item.get("name", query),
                    "address": cached_item.get("address", ""),
                    "rating": 0,
                    "isNewDiscovery": False  # 깃발 꽂지 마
                }
                
            # 2. 실시간 검색 기록 (30일 유효기간 체크 부활!)
            realtime_cache_key = f"result_{lang}"
            if realtime_cache_key in cached_item and cached_item[realtime_cache_key]:
                cache_date = datetime.strptime(cached_item["date"], "%Y-%m-%d")
                
                if datetime.now() - cache_date < timedelta(days=30):
                    # 30일 안 지났으면 바로 결과 보여주기
                    print(f"⚡ [DB 적중] '{query}' - 최근 30일 내 검색 기록 반환!")
                    result_data = cached_item[realtime_cache_key]
                    result_data["isNewDiscovery"] = False # 깃발 꽂지 마
                    return result_data
                else:
                    # 30일 지났으면? 아래 실시간 분석으로 내려보내서 최신화 진행!
                    print(f"🔄 [DB 갱신] '{query}' - 30일이 지나 최신 데이터로 다시 검색합니다.")

    # 💡 [포인트 2] 실시간 분석 (최초 발견이거나, 30일 지나서 갱신하는 경우)
    print(f"🔍 [실시간 분석] '{query}' AI 가동 중...")
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
                
                # DB 업데이트
                if collection is not None:
                    update_data = {
                        "name": query,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        f"result_{lang}": final_result
                    }
                    collection.update_one({"name": query}, {"$set": update_data}, upsert=True)
                    print(f"💾 [DB 저장] '{query}' 최신 분석 결과 저장 완료!")
                
                # 💡 [포인트 3] 방금 돌린 게 진짜 아예 처음 찾은 거면 True, 30일 갱신인 거면 False!
                final_result["isNewDiscovery"] = not already_existed 
                return final_result
                
        except: continue
        
    raise HTTPException(status_code=500, detail="분석 실패")

# ==========================================
# 💡 [지도 기능 1] 3.5점 이상일 때 깃발 저장하기 (POST)
# ==========================================
@app.post("/api/map-flags")
async def save_map_flag(request: Request):
    if collection is None:
        raise HTTPException(status_code=500, detail="DB 연결 실패")
    
    try:
        data = await request.json()
        name = data.get("name")
        address = data.get("address")
        score = data.get("score")

        if not name or score is None:
            raise HTTPException(status_code=400, detail="데이터 부족")

        # DB의 'places_cache' 컬렉션에 분석 결과 형식으로 저장합니다.
        # 이렇게 저장해야 나중에 GET으로 불러올 수 있습니다.
        update_data = {
            "name": name,
            "address": address,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "result_ko": {
                "name": name,
                "address": address,
                "realScore": score
            }
        }
        
        collection.update_one({"name": name}, {"$set": update_data}, upsert=True)
        print(f"💾 [DB 깃발 저장] {name} ({score}점)")
        return {"status": "success"}
    except Exception as e:
        print("🚨 깃발 저장 에러:", e)
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 💡 [지도 기능 2] DB에서 3.5점 이상 깃발들 가져오기 (GET)
# ==========================================
@app.get("/api/map-flags")
def get_map_flags():
    if collection is None:
        return []
        
    flags = []
    try:
        # DB에서 분석 결과('result_ko')가 있는 데이터를 모두 찾습니다.
        docs = collection.find({"result_ko": {"$exists": True}})
        
        for doc in docs:
            data = doc["result_ko"]
            score = data.get("realScore", 0)
            
            # 3.5점 이상인 것만 깃발 리스트에 담기
            if score >= 3.5:
                flags.append({
                    "name": data.get("name", doc.get("name")),
                    "address": data.get("address", doc.get("address")),
                    "score": score
                })
        return flags
    except Exception as e:
        print("🚨 깃발 불러오기 에러:", e)
        return []

# 🚀 서버 실행 코드 (무조건 맨 마지막에 있어야 함!)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))