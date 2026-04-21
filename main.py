import os
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scraper import search_and_get_reviews 
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
from openai import OpenAI  # 💡 구글 대신 OpenAI 수입!
from fastapi import BackgroundTasks  # 이거 추가 (기존 FastAPI 줄에 넣거나 밑에 따로 빼도 됨)
from kakao_scraper import get_kakao_place_id, get_deep_kakao_reviews  # 💡 방금 만든 무기 장착!


load_dotenv()

# ==========================================
# 💡 OpenAI 클라이언트 설정 (.env의 OPENAI_API_KEY 사용)
# ==========================================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# 💡 MongoDB 클라우드 연결 설정
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
try:
    mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = mongo_client["jjin_view_db"]
    collection = db["places_cache"]
    print("✅ MongoDB 클라우드 연결 성공!")
except Exception as e:
    print(f"🚨 MongoDB 연결 실패 (URI를 확인하세요): {e}")
    collection = None

last_queries = {} 

# --- Rate Limit 설정 ---
user_requests = defaultdict(list)
# 💡 사용자님의 요청대로 하루 검색 기회를 시원하게 1500번으로 늘렸습니다!
RATE_LIMIT = 1500 
WINDOW_SECONDS = 86400 # 60초가 아니라 하루(86400초) 기준으로 1500번 체크

# --- 동적 프롬프트 생성 ---
def get_fast_prompt(lang, place_info):
    if lang == "en":
        instruction = "You are a 'Cold-blooded Restaurant Profiler'. Evaluate the reviews strictly."
        guidelines = "Identify fake patterns. Base score 3.0. Deduct for bad hygiene/service."
        json_format = '{ "translatedName": "Name", "translatedAddress": "Address", "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "Critical summary in 2-3 sentences", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    else:
        instruction = "당신은 광고성 리뷰를 걸러내는 '냉혹한 미식 프로파일러'입니다."
        guidelines = "리뷰 이벤트 정황(영혼없는 5점, 서비스 언급)을 찾아내고, 기준점 3.0점에서 감점하세요."
        json_format = '{ "translatedName": "가게 이름", "translatedAddress": "가게 주소", "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "리뷰 분석 결과를 핵심만 2~3줄로 짧고 명확하게 요약하세요. (위생, 조작 확률 위주로)", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nInput Data: Name: {place_info['name']}\nReviews: {' '.join(place_info['reviews'])}"

def get_deep_prompt(lang, place_name, reviews):
    reviews_text = "\n".join(reviews)
    if lang == "en":
        instruction = "You are a 'Cold-blooded Restaurant Profiler' analyzing 25 deep reviews to uncover the truth."
        guidelines = "[Detection & Weighting]\n1. High 'eventProbability' for keywords like 'free drink', or if 5-star reviews lack food details.\n2. Give 2x weight to 1~3 star reviews specifying issues.\n3. Ignore blind 5-stars from habitual 5-star reviewers (avg > 4.8).\n[Balanced Scoring Rules]\n4. Base Score: 3.0. Max 2.9 if eventProbability > 70%.\n5. Proportional Deductions: Deduct -0.2 to -0.8 for systemic hygiene/rude service, and -0.1 to -0.5 for overpriced/long waits."
        json_format = '{ "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "Write in two paragraphs. Paragraph 1 starts with \'🔍 [Reason]\'. Paragraph 2 starts with \'🚨 [Conclusion]\'.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    else:
        instruction = "당신은 조작된 평점을 파괴하는 '냉혹한 심층 미식 프로파일러'입니다. 25개의 카카오 리뷰를 분석하세요."
        guidelines = "[리뷰 이벤트 및 조작 패턴 감지]\n1. '서비스 받았어요' 등 보이면 'eventProbability' 대폭 상승.\n2. 음식 묘사 없이 '친절해요'만 있는 5점은 보상형 의심.\n3. 단점 지적한 1~3점 리뷰에 2배 가중치.\n[🔥 리뷰어 성향 판별법]\n4. 깐깐한 미식가(평균 3.5 이하)의 5점은 가중치 UP, 습관성 만점자(평균 4.8 이상)의 영혼 없는 5점은 무시.\n[균형 잡힌 채점 기준]\n5. 기준점 3.0점. 상한선: eventProbability 70% 이상이면 최대 2.9점.\n6. 유연한 감점: 전체 리뷰 중 단점 비율 고려. 빈도에 따라 위생/불친절(-0.2~-0.8), 가성비/웨이팅(-0.1~-0.5) 차감."
        json_format = '{ "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "반드시 두 문단으로 작성. 첫 문단은 \'🔍 [분석 근거]\'로 시작하여 구체적 이유(위생 문제 빈도, 조작 정황 등) 서술, 두 번째 문단은 줄바꿈 후 \'🚨 [최종 결론]\'으로 시작하여 평가.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nTarget: {place_name}\nReviews: {reviews_text}"


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
                content={"detail": "하루 검색 횟수를 모두 사용하셨습니다! 내일 다시 찾아주세요. 🚀"}
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

def run_kakao_advanced_analysis(query: str, place_name: str, lang: str):
    print(f"🏃‍♂️ [백그라운드] '{place_name}' 카카오 심층 분석 시작...")
    
    place_id = get_kakao_place_id(place_name)
    if not place_id: return

    reviews = get_deep_kakao_reviews(place_id)
    if len(reviews) < 5: return

    try:
        prompt = get_deep_prompt(lang, place_name, reviews)
        response = client.chat.completions.create(
            model="gpt-4o-mini", response_format={ "type": "json_object" },
            messages=[{"role": "system", "content": "You are a JSON generating assistant."}, {"role": "user", "content": prompt}]
        )
        ai_data = json.loads(response.choices[0].message.content)
        
        if collection is not None:
            collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": ai_data}})
            print(f"🔥 [백그라운드 완료] '{place_name}' 고급 분석 DB 저장 완료!")
    except Exception as e:
        print(f"🚨 심층 분석 에러: {e}")

@app.post("/api/analyze")
async def analyze_place(request: Request, background_tasks: BackgroundTasks): # 💡 인자에 이거 꼭 추가!
    global last_queries
    client_ip = request.client.host
    try: data = await request.json()
    except: data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    if query: query = query[:100]
    lang = data.get("lang") or "ko"
    
    # 1. DB 캐시 확인 (카카오 결과가 있으면 같이 보냄)
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
                        result_data["has_advanced"] = True
                        result_data["kakao_data"] = cached_item[kakao_cache_key]
                    else:
                        result_data["has_advanced"] = False
                        background_tasks.add_task(run_kakao_advanced_analysis, query, result_data["name"], lang)
                        
                    return result_data

    # 2. 캐시 없으면 실시간 구글 분석 (빠른 요약)
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
            update_data = {"name": query, "date": datetime.now().strftime("%Y-%m-%d"), f"result_{lang}": final_result}
            collection.update_one({"name": query}, {"$set": update_data}, upsert=True)
        
        # 💡 유저한테 답 주기 전에 카카오 요원을 뒤로 파견!
        background_tasks.add_task(run_kakao_advanced_analysis, query, place_info['name'], lang)
        
        return final_result

    except Exception as e:
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
        aiSummary = data.get("aiSummary") 
        details = data.get("details")     

        if not name or score is None:
            raise HTTPException(status_code=400, detail="데이터 부족")

        update_data = {
            "name": name,
            "address": address,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "result_ko": {
                "name": name,
                "address": address,
                "realScore": score,
                "aiSummary": aiSummary,  
                "details": details       
            }
        }
        
        collection.update_one({"name": name}, {"$set": update_data}, upsert=True)
        print(f"💾 [DB 깃발 저장 완료] {name} ({score}점, 요약/상세 포함)")
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
        docs = collection.find({"result_ko": {"$exists": True}})
        
        for doc in docs:
            data = doc["result_ko"]
            score = data.get("realScore", 0)
            
            if score >= 3.5:
                flags.append({
                    "name": data.get("name", doc.get("name")),
                    "address": data.get("address", doc.get("address")),
                    "score": score,
                    "aiSummary": data.get("aiSummary", ""), 
                    "details": data.get("details", None)    
                })
        return flags
    except Exception as e:
        print("🚨 깃발 불러오기 에러:", e)
        return []
   
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))