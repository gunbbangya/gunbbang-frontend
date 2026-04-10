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
# 💡 [핵심] API 키 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"
last_queries = {} 

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 캐시 관련 함수 (동일)
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
        
        # 융단폭격 맵핑 유지
        return [{
            "id": result.get("name"),
            "place_name": result.get("name"),
            "name": result.get("name"),
            "address_name": result.get("address"),
            "road_address_name": result.get("address"),
            "address": result.get("address"),
            "place_url": result.get("name"),
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

    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info: raise HTTPException(status_code=404)

    try:
        # 🔍 [자가진단] 현재 사용 가능한 모델 리스트를 로그에 출력 (터미널에서 확인 가능)
        print("--- [사용 가능한 모델 리스트 확인] ---")
        for m in genai.list_models():
            print(f"Model: {m.name}, Methods: {m.supported_generation_methods}")
        
        # 💡 [진짜 필살기] 모델 객체를 생성할 때, 'v1beta'를 우회하는 설정 시도
        # 만약 라이브러리가 v1beta를 고집한다면, 아예 가장 구형이자 안정적인 'gemini-pro'를 우선 호출해보겠습니다.
        model = genai.GenerativeModel('gemini-pro') 
        
        prompt = f"""
        식당 분석 보고서를 JSON 형식으로 작성하라.
        식당명: {place_info['name']}
        평점: {place_info['rating']}
        리뷰수: {place_info.get('user_ratings_total', 0)}
        리뷰: {" ".join(place_info['reviews'])}

        반드시 아래 JSON 구조만 출력하라:
        {{
            "realScore": 1.0~5.0,
            "aiSummary": "요약",
            "details": {{ "taste": "1~5/데이터 부족", "value": "1~5/데이터 부족", "service": "1~5/데이터 부족", "time": "1~5/데이터 부족", "hygiene": "1~5/데이터 부족" }}
        }}
        """

        response = model.generate_content(prompt)
        
        # 정규식 파싱 (안전빵)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        ai_data = json.loads(match.group())
        
        final_result = {**ai_data, "name": place_info['name'], "address": place_info['address'], "rating": place_info['rating']}
        cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
        save_cache(cache)
        return final_result
        
    except Exception as e:
        print(f"❌ 분석 최종 실패: {e}")
        # 만약 또 404가 뜨면, 라이브러리가 강제로 v1beta를 쓰고 있다는 뜻입니다.
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
