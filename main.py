import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews 
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

        # 💡 [해결책] 프론트엔드가 어떤 변수명을 쓰든 다 걸리게 샷건 방식으로 보냅니다.
        formatted_result = {
            "id": result["name"],
            "place_name": result["name"],       # 카카오 표준
            "name": result["name"],             # 구글/일반 표준
            "title": result["name"],            # 가끔 쓰이는 표준
            "address_name": result["address"],   # 카카오 주소
            "road_address_name": result["address"],
            "address": result["address"],        # 일반 주소
            "place_url": result["name"],         # 클릭 시 analyze에 전달될 핵심 값
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

    # query가 비어있으면 마지막 검색어로 대체 (422 에러 방어)
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석 대상이 없습니다.")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

    try:
        gourmet_model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = f"식당명: {place_info['name']}\n리뷰를 분석해서 광고 없는 진짜 정보를 JSON으로 줘.\n리뷰:\n" + "\n".join(place_info['reviews'])
        response = gourmet_model.generate_content(prompt)
        ai_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        final_result = {**ai_data, "name": place_info['name'], "address": place_info['address'], "rating": place_info['rating']}
        cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
        save_cache(cache)
        return final_result
    except:
        raise HTTPException(status_code=500, detail="AI 분석 중 오류")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
