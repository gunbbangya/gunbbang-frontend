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

# 1. 환경 설정
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

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
def search_places(q: str):
    try:
        result = search_and_get_reviews(q)
        if not result: return []
        
        # 💡 [해결책 1] 프론트엔드가 어떤 필드를 요구할지 모르니 다 넣어줍니다. (id, query, place_name 모두 지원)
        formatted_result = {
            "id": result["name"],
            "query": result["name"],
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"]
        }
        return [formatted_result]
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_place(request: Request):
    # 💡 [해결책 2] 바디(JSON)뿐만 아니라 URL 파라미터에서도 이름을 뒤져봅니다.
    data = {}
    try:
        data = await request.json()
        print(f"DEBUG: 프론트 바디 데이터 -> {data}")
    except:
        print("DEBUG: 바디 데이터 없음")

    # 우선순위: 바디의 query -> 바디의 id -> 바디의 place_name -> URL의 q 파라미터
    query = (
        data.get("query") or 
        data.get("id") or 
        data.get("place_name") or 
        request.query_params.get("q") or 
        request.query_params.get("query")
    )
    lang = data.get("lang") or "ko"

    if not query:
        print(f"🚨 [에러] 분석할 이름이 끝까지 없음. 수신 데이터: {data}")
        raise HTTPException(status_code=422, detail="분석할 식당 정보(query)가 누락되었습니다.")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    # 데이터 수집 (구글 검색)
    place_info = search_and_get_reviews(query)
    if not place_info or not place_info.get('reviews'):
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        prompt = f"식당명: {place_info['name']}\n명령: 아래 리뷰를 분석하고, 결과는 '{lang}' 언어로 작성해. JSON만 반환.\n리뷰:\n{reviews_text}"
        response = gourmet_model.generate_content(prompt)
        
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        try:
            ai_data = json.loads(cleaned_text)
        except:
            ai_data = {"realScore": 0, "aiSummary": "AI 분석 형식 오류", "details": {"taste": 0, "value": 0, "service": 0, "time": 0}}
        
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
