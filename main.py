import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
# 반드시 scraper.py에 search_and_get_reviews 함수가 있어야 합니다.
from scraper import search_and_get_reviews 
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Optional

# 1. 환경 설정 및 API 키 로드
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

# 💡 [치명적 실수 수정] 변수를 함수 밖에서 미리 선언해야 합니다.
last_queries = {}

# AI 시스템 지침
system_prompt = """
당신은 전 세계 식당 리뷰의 진실을 파헤치는 '글로벌 데이터 프로파일러 AI'입니다.
구글 맵스 리뷰 데이터를 바탕으로, 광고성 글과 무지성 칭찬을 걸러내고 '진짜 경험'만 추출하세요.
반드시 JSON 형식으로만 답변하세요.
{
    "realScore": 1.0~5.0,
    "aiSummary": "3줄 요약평",
    "details": { "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5 }
}
"""

gourmet_model = genai.GenerativeModel(
    'gemini-1.5-flash', # 혹은 파운더님이 사용하시는 모델명 확인
    system_instruction=system_prompt,
    generation_config={"response_mime_type": "application/json"}
)

# 캐시 관리 함수
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

# 1. 검색 엔드포인트: 'documents' 포장지 추가
@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries # 미리 선언된 변수를 사용합니다.
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q # 프론트가 이름을 안 보낼 때를 대비해 기억함
        
        result = search_and_get_reviews(q)
        if not result: return {"documents": []}
        
        # 프론트엔드(Next.js)가 기대하는 카카오식 데이터 구조
        formatted_result = {
            "id": result["name"],
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": f"https://www.google.com/search?q={result['name']}",
            "category_name": "식당"
        }
        
        # 💡 리스트를 'documents'라는 키에 담아줘야 화면에 나타납니다.
        return {"documents": [formatted_result]}
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. 분석 엔드포인트: 유연한 데이터 수신
@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    
    try:
        data = await request.json()
        print(f"DEBUG: 프론트 전송 데이터 -> {data}")
    except:
        data = {}

    # query가 없으면 마지막 검색어(last_queries)를 가져옴
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석할 식당 정보(query)가 누락되었습니다.")

    print(f"✅ 분석 대상 확정: {query}")

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
