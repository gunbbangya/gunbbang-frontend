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

# AI 시스템 지침
system_prompt = """
당신은 전 세계 식당 리뷰의 진실을 파헤치는 '글로벌 데이터 프로파일러 AI'입니다.
구글 맵스 리뷰 데이터를 바탕으로, 광고성 글과 무지성 칭찬을 걸러내고 '진짜 경험'만 추출하세요.

[출력 형식]
반드시 아래의 JSON 형식으로만 답변을 반환하세요.
{
    "realScore": 1.0~5.0 (소수점 한자리),
    "aiSummary": "3줄 요약평",
    "details": { "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5 }
}
"""

gourmet_model = genai.GenerativeModel(
    'gemini-1.0-pro',
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

# CORS 설정: Vercel 등 외부 접속 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 검색 엔드포인트: 프론트엔드가 요구하는 'id'를 강제로 부여함
@app.get("/api/search")
def search_places(q: str):
    try:
        result = search_and_get_reviews(q)
        if not result: return []
        
        # 프론트엔드 호환용 데이터 포장
        formatted_result = {
            "id": result["name"], # 식당 이름을 id로 사용하여 분석 시 유실 방지
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"]
        }
        return [formatted_result]
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 분석 엔드포인트: 422 에러 방지를 위해 유연한 데이터 수신 처리
@app.post("/api/analyze")
async def analyze_place(request: Request):
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=422, detail="JSON 데이터가 비어있습니다.")

    # query, id, place_name 중 무엇으로 오든 식당 이름으로 인식 (눈치껏 처리)
    query = data.get("query") or data.get("id") or data.get("place_name")
    lang = data.get("lang") or "ko"

    if not query:
        print(f"🚨 데이터 누락 발생: {data}")
        raise HTTPException(status_code=422, detail="분석할 식당 정보(query)가 누락되었습니다.")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    print(f"\n[서버] '{query}' 분석 시작...")
    place_info = search_and_get_reviews(query)

    if not place_info or not place_info.get('reviews'):
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        prompt = f"식당명: {place_info['name']}\n명령: 아래 리뷰를 분석하고, 결과는 '{lang}' 언어로 작성해. JSON만 출력.\n리뷰:\n{reviews_text}"
        response = gourmet_model.generate_content(prompt)
        
        # JSON 세탁
        raw_text = response.text.strip()
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        try:
            ai_data = json.loads(cleaned_text)
        except:
            ai_data = {
                "realScore": 0, "aiSummary": "분석 결과 처리 오류",
                "details": {"taste": 0, "value": 0, "service": 0, "time": 0}
            }
        
        final_result = {
            **ai_data,
            "name": place_info['name'],
            "address": place_info['address'],
            "rating": place_info['rating']
        }

        cache[query] = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "result": final_result
        }
        save_cache(cache)
        return final_result
        
    except Exception as e:
        print(f"AI 분석 에러: {e}")
        raise HTTPException(status_code=500, detail="분석 중 오류가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
