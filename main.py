import os
import json
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews 
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"
last_queries = {} 

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

        formatted_result = {
            "id": result["name"],
            "place_name": result["name"],
            "name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "address": result["address"],
            "place_url": result["name"], 
            "category_name": "음식점",
            "phone": "Google Maps"
        }
        return [formatted_result]
    except:
        return []

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    try:
        data = await request.json()
    except:
        data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="대상 누락")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        # 💡 [변경됨] 캐시 유지 기간을 7일에서 30일(한 달)로 늘렸습니다.
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            print(f"📦 [캐시 사용] '{query}'의 데이터를 파일에서 불러옵니다.")
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404, detail="정보 없음")

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        식당 '{place_info['name']}'의 리뷰를 분석해서 진짜 정보를 JSON으로만 답해.
        {{
            "realScore": 1.0~5.0,
            "aiSummary": "3줄 요약",
            "details": {{ "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5 }}
        }}
        리뷰 내용: {" ".join(place_info['reviews'])}
        """
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 💡 [필살기] AI 대답에서 JSON 부분만 강제로 추출 (500 에러 방지)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            ai_data = json.loads(match.group())
        else:
            raise ValueError("AI 응답에서 JSON을 찾을 수 없음")
        
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
        print(f"❌ AI 분석 에러: {str(e)}")
        raise HTTPException(status_code=500, detail="분석 실패")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
