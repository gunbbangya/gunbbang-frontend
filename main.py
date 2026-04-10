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

# 💡 [최종 고도화] 범용적 볼륨 판독 지침이 이식된 시스템 프롬프트
system_prompt = """
당신은 식당의 실체를 파헤치는 '글로벌 리스크 프로파일러 AI'입니다. 
제공된 메타데이터와 리뷰 텍스트를 바탕으로 엄격하게 분석하십시오.

[리뷰 볼륨 판독 지침 - 범용 표준]
1. 50개 미만 (미검증): 데이터 신뢰도가 낮음. 평점이 높아도 '신규 또는 지인 기반' 가능성을 염두에 두고 보수적으로 평가할 것.
2. 500개 이상 (검증됨): 표본의 안정성이 확보됨. 평점이 4.0 이상이면 실패 확률이 극히 낮은 '강력 추천' 식당.
3. 1,000개 이상 (랜드마크): 글로벌 기준 대형 맛집. 이 규모에서 평점 3.5점 이상만 유지해도 '상위 10%의 검증된 맛집'으로 인정할 것.
4. 위험 경보: 리뷰가 500개 이상임에도 평점이 3.0 미만이라면, 서비스나 위생에 '고질적이고 치명적인 문제'가 있는 것으로 규정할 것.

[데이터 분석 규칙]
- 추측 금지: 맛, 가성비, 서비스, 시간, 위생 항목 중 리뷰 텍스트에서 근거를 찾을 수 없는 경우, 점수 대신 반드시 "데이터 부족"으로 기재하십시오.
- 네거티브 필터링: 위생, 식중독, 사기적 가격 등 치명적 위협은 요약문 최상단에 [위험] 태그와 함께 기재하십시오.
- 마케팅 제외: '재방문' 등 상투적 광고 멘트는 가점 요인에서 배제하십시오.

[출력 형식 - JSON]
{
    "realScore": 1.0~5.0 (종합 평점),
    "aiSummary": "지뢰 여부 및 핵심 요약 (3줄 이내)",
    "details": {
        "taste": "1~5 또는 데이터 부족",
        "value": "1~5 또는 데이터 부족",
        "service": "1~5 또는 데이터 부족",
        "time": "1~5 또는 데이터 부족",
        "hygiene": "1~5 또는 데이터 부족"
    }
}
"""

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

        return [{
            "id": result["name"],
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"],
            "category_name": "식당",
            "phone": ""
        }]
    except: return []

@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    try:
        data = await request.json()
    except: data = {}

    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="Query missing")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404, detail="No info")

    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_prompt,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )
        
        # 💡 전체 리뷰 수와 평점 데이터를 AI에게 명확히 전달
        user_prompt = f"""
        식당명: {place_info['name']}
        공식 평점: {place_info['rating']}
        결과 언어: {lang}
        리뷰 내용:
        {" ".join(place_info['reviews'])}
        """
        
        response = model.generate_content(user_prompt)
        ai_data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
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
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
