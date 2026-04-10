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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
        
        # 💡 [해결] 프론트엔드가 어떤 키를 찾든 대응하도록 "다 넣어주는" 리턴 방식
        # 가게 이름(name)을 최우선으로 배치
        return [{
            "id": result.get("name"),
            "place_name": result.get("name"),        # 프론트엔드 관례 1
            "name": result.get("name"),              # 구글/표준 관례 2
            "address_name": result.get("address"),   # 카카오 맵 템플릿 관례
            "road_address_name": result.get("address"),
            "address": result.get("address"),        # 일반 변수 관례
            "place_url": result.get("name"),         # 식별자
            "category_name": "음식점"
        }]
    except Exception as e:
        print(f"🚨 검색 API 에러: {e}")
        return []

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    try:
        data = await request.json()
    except: data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info: raise HTTPException(status_code=404)

    try:
        # 💡 [필살기] 404 에러 원천 차단: 'JSON 모드'를 빼고 표준 통로를 탑니다.
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        식당: {place_info['name']} (평점: {place_info['rating']}, 리뷰수: {place_info.get('user_ratings_total', 0)})
        결과 언어: {lang}

        [지뢰 탐지 지침]
        1. 볼륨 판독: 500개 이상/4.0점 이상이면 강력 추천. 1,000개 이상/3.5점 이상이면 랜드마크 맛집.
        2. 지뢰 경고: 위생, 식중독, 불친절, 바가지 언급 시 [위험] 경고.
        3. 데이터 정직성: 특정 항목(맛, 가성비, 서비스, 시간, 위생) 근거 없으면 반드시 "데이터 부족" 표기.
        4. 마케팅 배제: 상투적인 재방문 멘트는 무시.

        반드시 아래의 JSON 형식을 지켜서 답변하세요:
        {{
            "realScore": 1.0~5.0,
            "aiSummary": "요약 3줄 이내",
            "details": {{
                "taste": "1~5 또는 데이터 부족",
                "value": "1~5 또는 데이터 부족",
                "service": "1~5 또는 데이터 부족",
                "time": "1~5 또는 데이터 부족",
                "hygiene": "1~5 또는 데이터 부족"
            }}
        }}

        리뷰 데이터:
        {" ".join(place_info['reviews'])}
        """

        # JSON 모드를 해제하여 v1beta 접속을 방지함
        response = model.generate_content(prompt)
        
        # 💡 정규표현식으로 텍스트 응답 중 JSON 블록만 추출
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            raise ValueError("AI 응답에서 JSON을 찾을 수 없습니다.")
            
        ai_data = json.loads(match.group())
        
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
        print(f"❌ 분석 최종 실패: {e}")
        raise HTTPException(status_code=500, detail="AI 분석 서버 오류")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
