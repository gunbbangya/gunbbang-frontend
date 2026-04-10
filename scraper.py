import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews # 주신 scraper.py (공식 API 버전) 호출
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 초기 설정
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

# 💡 [필수] 전역 변수 선언 (함수 밖에서 미리 선언)
last_queries = {}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📂 캐시 관리 함수
def load_cache():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

# 2. 검색 엔드포인트: 어제 성공했던 리스트([]) 형식으로 복구
@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q # 비상용 저장

        # scraper.py에서 구글 API 결과 가져옴
        result = search_and_get_reviews(q)
        if not result:
            return []

        # 💡 프론트엔드 UI가 읽을 수 있는 어제의 그 데이터 형식
        formatted_result = {
            "id": result["name"], 
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"], # 프론트가 분석 시 사용하는 키
            "category_name": "식당",
            "phone": ""
        }
        
        # 어제처럼 리스트 안에 객체를 담아 보냄
        return [formatted_result]
        
    except Exception as e:
        print(f"❌ 검색 에러: {e}")
        return []

# 3. 분석 엔드포인트: 어제와 동일한 로직
@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    
    try:
        data = await request.json()
    except:
        data = {}

    # 프론트가 주는 데이터 중 뭐라도 있으면 잡음
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석할 대상을 찾을 수 없습니다.")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    # 4. 리뷰 가져오기 및 AI 분석
    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404, detail="리뷰를 가져올 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        # 어제와 동일한 AI 모델 설정
        gourmet_model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"식당명: {place_info['name']}\n명령: 리뷰를 분석해서 JSON만 반환해.\n리뷰:\n{reviews_text}"
        response = gourmet_model.generate_content(prompt)
        
        ai_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        final_result = {
            **ai_data,
            "name": place_info['name'],
            "address": place_info['address'],
            "rating": place_info['rating']
        }

        cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
        save_cache(cache)
        return final_result
        
    except Exception as e:
        print(f"AI 분석 에러: {e}")
        raise HTTPException(status_code=500, detail="분석 중 오류 발생")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
