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

# 1. 환경 설정 및 API 키 장착
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

# =====================================================================
# 🧠 AI 시스템 지침 (글로벌 구글맵 버전)
# =====================================================================
system_prompt = """
당신은 전 세계 식당 리뷰의 진실을 파헤치는 '글로벌 데이터 프로파일러 AI'입니다.
구글 맵스 리뷰 데이터를 바탕으로, 광고성 글과 무지성 칭찬을 걸러내고 '진짜 경험'만 추출하세요.

[출력 형식]
반드시 아래의 JSON 형식으로만 답변을 반환해 주세요.
{
    "realScore": 1.0에서 5.0 사이의 소수점 한 자리 숫자 (프로파일링을 거친 진짜 평점),
    "aiSummary": "거짓/이벤트 리뷰를 제외하고, 신뢰도 높은 리뷰어들이 꼽은 진짜 장단점을 종합한 3줄 요약평",
    "details": {
        "taste": 1에서 5 사이의 정수,
        "value": 1에서 5 사이의 정수,
        "service": 1에서 5 사이의 정수,
        "time": 1에서 5 사이의 정수
    }
}
"""

gourmet_model = genai.GenerativeModel(
    'gemini-1.0-pro',
    system_instruction=system_prompt,
    generation_config={"response_mime_type": "application/json"}
)

# =====================================================================
# 📂 데이터베이스(캐시) 관리
# =====================================================================
def load_cache():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

# =====================================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 🚨 Vercel 프론트엔드 연결 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    query: str
    lang: Optional[str] = "ko" # 프론트에서 보낸 언어 설정 (기본값 한국어)

@app.get("/api/search")
def search_places(q: str):
    try:
        result = search_and_get_reviews(q)
        if not result:
            return []
        
        # 구글 데이터를 프론트엔드가 알아듣게 기존 형식으로 포장
        formatted_result = {
            "place_name": result["name"],
            "address_name": result["address"],
            "place_url": result["name"]  # URL 대신 이름 자체를 넘김
        }
        return [formatted_result] 
        
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
def analyze_place(request: AnalyzeRequest):
    query = request.query
    lang = request.lang
    
    cache = load_cache()

    # 1. 캐시 확인
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            print(f"⚡ [캐시 적중] {query}")
            return cached_item["result"]

    # 2. 구글 데이터 수집
    print(f"\n[서버] 글로벌 식당 '{query}' 분석 시작!")
    place_info = search_and_get_reviews(query)

    if not place_info or not place_info.get('reviews'):
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

    # 3. AI 분석
    print(f"[서버] 글로벌 제미나이 가동... (출력 언어: {lang})")
    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        prompt = f"식당명: {place_info['name']}\n명령: 아래 리뷰를 분석하고, 최종 결과는 반드시 '{lang}' 언어로만 작성해.\n리뷰:\n{reviews_text}"
        response = gourmet_model.generate_content(prompt)
        
        # JSON 텍스트 세탁
        raw_text = response.text
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
            
        cleaned_text = cleaned_text.strip() 
        
        try:
            ai_data = json.loads(cleaned_text)
        except json.JSONDecodeError as json_err:
            print(f"🚨 JSON 파싱 에러: {json_err}")
            ai_data = {
                "realScore": 0,
                "aiSummary": "AI 분석 중 오류가 발생했습니다.",
                "details": { "taste": 0, "value": 0, "service": 0, "time": 0 }
            }
        
        # 결과 합치기
        final_result = {
            **ai_data,
            "name": place_info['name'],
            "address": place_info['address'],
            "rating": place_info['rating']
        }

        # 4. 캐시 저장
        cache[query] = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "result": final_result
        }
        save_cache(cache)
        
        return final_result
        
    except Exception as e:
        print(f"에러 발생: {e}")
        raise HTTPException(status_code=500, detail="판독 중 에러가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
