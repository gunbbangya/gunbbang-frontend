import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews 
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 설정 및 API 키 장착
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

# AI 시스템 지침 (글로벌 버전)
system_prompt = """
당신은 전 세계 식당 리뷰의 진실을 파헤치는 '글로벌 데이터 프로파일러 AI'입니다.
구글 맵스 리뷰 데이터를 바탕으로, 광고성 글과 무지성 칭찬을 걸러내고 '진짜 경험'만 추출하세요.
반드시 JSON 형식으로만 답변하세요.
{
    "realScore": 1.0~5.0,
    "aiSummary": "3줄 요약",
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

class AnalyzeRequest(BaseModel):
    query: str
    lang: str = "ko"  # 👈 언어 정보 받을 바구니 추가! (기본값은 한국어)

@app.get("/api/search")
def search_places(q: str):
    try:
        result = search_and_get_reviews(q)
        if not result:
            return []
        # 프론트엔드가 배열 형식을 기다리므로 리스트로 반환
        return [result] 
    except Exception as e:
        print(f"검색 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
def analyze_place(request: AnalyzeRequest):
    query = request.query
    lang = request.lang  # 👈 프론트에서 보낸 언어 꺼내기!
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
        
        # JSON 세탁
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(cleaned_text)
        
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