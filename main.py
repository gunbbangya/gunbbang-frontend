import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"
# 💡 [비기] 프론트가 이름을 안 보내줄 때를 대비해 마지막 검색어를 메모리에 저장합니다.
last_searched_query = {}

system_prompt = """
당신은 전 세계 식당 리뷰의 진실을 파헤치는 '글로벌 데이터 프로파일러 AI'입니다.
반드시 JSON 형식으로만 답변하세요.
{
    "realScore": 1.0~5.0,
    "aiSummary": "3줄 요약평",
    "details": { "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5 }
}
"""

gourmet_model = genai.GenerativeModel(
    'gemini-1.0-pro',
    system_instruction=system_prompt,
    generation_config={"response_mime_type": "application/json"}
)

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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        if not result: return {"documents": []} # 빈 배열도 포장해서 전송
        
        # 💡 핵심: 프론트엔드가 인식할 수 있게 'documents' 바구니에 담아줍니다.
        formatted_result = {
            "id": result["name"],
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": f"https://www.google.com/search?q={result['name']}",
            "category_name": "식당",
            "phone": ""
        }
        
        return {"documents": [formatted_result]} # 👈 이 포장지가 중요합니다.
        
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_searched_query
    client_ip = request.client.host
    
    try:
        data = await request.json()
        print(f"DEBUG: 수신 데이터 -> {data}")
    except:
        data = {}

    # 1순위: 바디 데이터 / 2순위: 메모리에 저장된 마지막 검색어 (필살기)
    query = (
        data.get("query") or 
        data.get("id") or 
        data.get("place_name") or 
        last_searched_query.get(client_ip)
    )
    lang = data.get("lang") or "ko"

    if not query:
        print(f"🚨 [치명적 에러] 이름 찾기 실패. 수신데이터: {data}, IP: {client_ip}")
        raise HTTPException(status_code=422, detail="분석할 식당 이름을 찾을 수 없습니다.")

    print(f"✅ 최종 결정된 분석 대상: {query}")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info or not place_info.get('reviews'):
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        prompt = f"식당명: {place_info['name']}\n명령: 아래 리뷰를 분석하고, 결과는 '{lang}' 언어로 작성해. JSON만 반환.\n리뷰:\n{reviews_text}"
        response = gourmet_model.generate_content(prompt)
        
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(cleaned_text)
        
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
