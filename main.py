import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews # 순환 참조 해결
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"
last_queries = {} # 비상용 메모리

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    with open(DB_FILE, "w", encoding="utf-8") as f: 
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q

        result = search_and_get_reviews(q)
        if not result: return []

        # 💡 어제 밤 성공했던 그 리스트 구조입니다.
        formatted_result = {
            "id": result["name"], 
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"], 
            "category_name": "식당",
            "phone": ""
        }
        return [formatted_result] # 리스트([])로 반환해야 목록이 뜹니다.
    except Exception as e:
        print(f"❌ 검색 에러: {e}")
        return []

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    try:
        data = await request.json()
    except:
        data = {}

    # 어제의 실패 요인이었던 query 누락을 last_queries로 보완
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석 대상을 찾을 수 없습니다.")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404, detail="식당 정보를 찾을 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        # 모델명은 파운더님의 환경에 맞게 1.5-flash 또는 1.0-pro 사용
        gourmet_model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = f"식당명: {place_info['name']}\n명령: 리뷰를 분석해서 JSON만 반환해.\n리뷰:\n{reviews_text}"
        response = gourmet_model.generate_content(prompt)
        
        # AI 응답 세탁
        ai_raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(ai_raw)
        
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
        print(f"❌ 분석 에러: {e}")
        raise HTTPException(status_code=500, detail="분석 중 오류 발생")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
