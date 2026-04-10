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

# 1. 환경 설정 및 API 키 로드
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

# 💡 전역 변수: 프론트에서 query를 누락할 경우를 대비한 메모리 저장소
last_queries = {}

system_prompt = """
당신은 전 세계 식당 리뷰의 진실을 파헤치는 '글로벌 데이터 프로파일러 AI'입니다.
구글 맵스 리뷰 데이터를 바탕으로 분석하세요. 반드시 JSON으로만 답변하세요.
{
    "realScore": 1.0~5.0,
    "aiSummary": "3줄 요약평",
    "details": { "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5 }
}
"""

gourmet_model = genai.GenerativeModel(
    'gemini-1.5-flash',
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
        if not result: return [] # 결과 없으면 빈 배열
        
        # 💡 [원상복구] 프론트엔드가 '배열'을 원하므로 다시 리스트로 보냅니다.
        # UI가 짤막하게 보이지 않도록 카테고리와 전화번호 필드를 더미 데이터로 채웠습니다.
        formatted_result = {
            "id": result["name"],
            "place_name": result["name"],
            "category_name": "음식점 > 식당",
            "category_group_name": "음식점",
            "phone": "정보 없음",
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"],  # 클릭 시 이 값이 analyze의 query로 전달됨
            "distance": ""
        }
        
        # 리스트([]) 형식으로 반환해야 프론트엔드 .map()이 작동합니다.
        return [formatted_result]
        
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    
    try:
        data = await request.json()
    except:
        data = {}

    # query가 비어있으면 마지막 검색어(last_queries)를 사용하여 422 에러 방어
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석할 대상을 찾을 수 없습니다.")

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
