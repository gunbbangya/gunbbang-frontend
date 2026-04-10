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

# 💡 [마스터 프롬프트] 파운더님의 철학과 지침 반영
system_prompt = """
당신은 식당의 실체를 파헤치는 '글로벌 리스크 프로파일러 AI'입니다.

[리뷰 볼륨 판독 지침]
- 50개 미만: '미검증' 상태. 평점이 높더라도 신뢰도를 낮게 측정할 것.
- 500개 이상: '검증된 표본'. 평점 4.0 이상이면 강력 추천.
- 1,000개 이상: '랜드마크'급 볼륨. 평점 3.5 이상만 되어도 검증된 맛집으로 인정.
- 예외: 리뷰 500개 이상인데 평점 3.0 미만이면 '고질적 문제가 있는 집'으로 규정.

[분석 규칙]
1. 치명적 단점 최우선: 위생, 식중독, 불친절, 바가지 언급 시 무조건 [위험] 경고.
2. 데이터 부재 시 처리: 특정 항목(맛, 가성비, 서비스, 시간, 위생)에 대해 근거가 없으면 반드시 "데이터 부족"으로 기재할 것.
3. 재방문 멘트 무시: 상투적인 광고 멘트는 가점 요인에서 배제.

[출력 형식 - JSON 전용]
{
    "realScore": 1.0~5.0,
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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def load_cache():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(cache_data, f, ensure_ascii=False, indent=4)

@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q
        result = search_and_get_reviews(q)
        if not result: return []

        # 💡 프론트엔드 목록 표시에 필요한 모든 키값 매칭
        return [{
            "id": result["name"],
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"],
            "category_name": "식당"
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

    if not query: raise HTTPException(status_code=422, detail="Missing query")

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info: raise HTTPException(status_code=404, detail="No info")

    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash', system_instruction=system_prompt)
        # AI에게 평점뿐만 아니라 '전체 리뷰 개수'도 함께 전달!
        user_prompt = f"""
        식당명: {place_info['name']}
        공식 평점: {place_info['rating']}
        전체 리뷰 수: {place_info['user_ratings_total']}
        결과 언어: {lang}
        리뷰 내용: {" ".join(place_info['reviews'])}
        """
        response = model.generate_content(user_prompt, generation_config={"temperature": 0.1})
        ai_data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        final_result = {**ai_data, "name": place_info['name'], "address": place_info['address'], "rating": place_info['rating']}
        cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
        save_cache(cache)
        return final_result
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
