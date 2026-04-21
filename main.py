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
        instruction = "You are a 'First-Line Fake Review Detector' analyzing 5 recent reviews. Base score is 2.5."
        guidelines = "[Detection Logic]\n1. Pattern Recognition: If multiple reviews share identical hashtags or specific keywords (e.g., 'date spot'), suspect a review event.\n2. Fatal Flaw: Even if positive reviews exist, if 1 review points out a 'fatal flaw' (hygiene, extreme rudeness), significantly lower the score.\n3. Scoring: 2.5 is a solid, no-fail spot. 3.0 is a local gem. 4.0 is a national tier. Set 'eventProbability' high if manipulation patterns are detected."
        json_format = '{ "translatedName": "Name", "translatedAddress": "Address", "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "1-2 sentence summary: Focus on fake patterns and whether there is a fatal experience-breaker.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    else:
        instruction = "당신은 5개의 리뷰에서 조작 패턴을 찾아내는 '1차 필터링 요원'입니다. 기준점은 2.5점입니다."
        guidelines = """
        [🔍 1차 방어선 감지 논리]
        1. 앵무새 패턴 감지: 특정 키워드나 해시태그가 반복되면 '보상형 리뷰'로 간주하고 조작 확률(eventProbability)을 대폭 높이세요.
        2. 치명적 결함(Fatal Flaw): 다른 칭찬이 많더라도 단 한 명이라도 위생이나 서비스에서 '경험을 완전히 망치는 치명적 문제'를 지적했다면 전체 평점을 크게 낮추세요.
        3. 점수 체계: 2.5점은 '실패 없는 집(평균)', 3.0점은 '검증된 맛집', 4.0점은 '전국구 맛집'입니다.
        """
        json_format = '{ "translatedName": "가게 이름", "translatedAddress": "가게 주소", "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "리뷰 조작 가능성과 치명적 단점 여부를 중심으로 1~2줄 요약하세요.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    
    return f"{instruction}\n{guidelines}\nReturn strictly in this JSON format:\n{json_format}\nInput Data: Name: {place_info['name']}\nReviews: {' '.join(place_info['reviews'])}"

def get_deep_prompt(lang, place_name, reviews):
    reviews_text = "\n".join(reviews)
    if lang == "en":
        instruction = "You are a 'Chief Culinary Profiler' analyzing 25 raw reviews. Base score is 2.5."
        guidelines = """
        [Deep Analysis Logic]
        1. Reviewer Profiling: Trust the 'strict critics' (avg score < 3.5). A 5-star from them is a real deal.
        2. Fatal Flaw Rule: Even if most reviews are positive, if there is a 'fatal flaw' (dirty environment, excessive waiting, staff hostility), lower the score significantly. One clear fatal issue is enough to lower the overall rating.
        3. Scoring: 2.5 is 'Good/No-Fail'. 3.0 is 'Excellent/Local Gem'. 4.0 is 'Legendary/National Tier'.
        4. Practical Tip: Extract one concrete tip (e.g., parking, hidden menu, best seats).
        """
        json_format = '{ "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "Para 1 (🔍 [Analysis]): Deep dive into reviewer credibility and fatal flaws. Para 2 (💡 [Visitor Tip]): One practical, actionable tip.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    else:
        instruction = "당신은 25개의 카카오 리뷰를 해부하는 '전문 미식 프로파일러'입니다. 기준점은 2.5점입니다."
        guidelines = """
        [💡 전문 분석가 감지 논리]
        1. 리뷰어 성향 파악: 평균 별점이 낮은 '엄격한 리뷰어'의 평가에 높은 가중치를 두세요. 단순히 좋다는 말보다 구체적인 맛의 묘사를 신뢰하세요.
        2. 치명적 단점 반영(Fatal Flaw): 아무리 평점 평균이 높아도, 위생 상태나 직원의 태도 등에서 치명적인 문제가 발견되면 점수를 대폭 삭감하세요. 단 한 건이라도 사실로 확인되는 치명적 단점은 대폭 감점의 근거가 됩니다.
        3. 점수 체계: 2.5점은 '실패 없는 괜찮은 집', 3.0점은 '정말 훌륭한 찐맛집', 4.0점은 '전국에서 찾아갈 만한 인생 맛집'입니다.
        4. 실전 꿀팁: 사용자가 방문 전 반드시 알아야 할 팁(주차, 대기 시간, 추천 메뉴 등)을 추출하세요.
        """
        json_format = '{ "realScore": 1.0~5.0, "eventProbability": 0~100, "aiSummary": "두 문단 작성. 첫 문단은 \'🔍 [심층 분석]\'으로 시작하여 리뷰어의 신뢰도와 치명적 단점 유무를 파악해 결론 도출. 두 번째 문단은 줄바꿈 후 \'💡 [실전 꿀팁]\'으로 시작하여 유용한 정보 한 줄 제공.", "details": { "taste": "1~5", "value": "1~5", "service": "1~5", "time": "1~5", "hygiene": "1~5" } }'
    
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
            
            if collection is not None:
                collection.update_one({"name": query}, {"$set": {f"kakao_result_{lang}": ai_data}})
                print(f"🔥 [크롤러 완료] '{search_keyword}' 고급 분석 DB 저장 완료!")
                
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