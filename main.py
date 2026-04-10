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

# 캐시 함수 생략 (기존과 동일)
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
        
        # 💡 [UI 원복] 절대 다른 글자를 섞지 않고 '순수한 이름'만 보냅니다.
        return [{
            "id": result["name"],
            "place_name": result["name"],      # 프론트엔드가 찾는 핵심 키
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"],       # 분석 요청 시 사용됨
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
        # 💡 [필살기] 404 에러 방지: 베타 설정(JSON 모드 등)을 모두 제거하고 표준 v1 모델 호출
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 프롬프트에 모든 지침을 합쳐서 보냄 (v1beta 충돌 원천 차단)
        prompt = f"""
        식당 정보: {place_info['name']} (평점: {place_info['rating']}, 리뷰수: {place_info.get('user_ratings_total', 0)})
        
        [지침]
        당신은 '글로벌 리스크 프로파일러'입니다. 리뷰를 분석해 진짜 평점을 매기세요.
        - 500개 이상 리뷰/4.0 평점 이상: 강력 추천.
        - 위생, 불친절, 바가지 언급 시 무조건 [위험] 경고.
        - 정보가 없는 항목은 반드시 "데이터 부족"으로 표기.
        
        반드시 아래 JSON 형식으로만 답변하세요:
        {{
            "realScore": 1.0~5.0,
            "aiSummary": "요약",
            "details": {{ "taste": "1~5/데이터 부족", "value": "1~5/데이터 부족", "service": "1~5/데이터 부족", "time": "1~5/데이터 부족", "hygiene": "1~5/데이터 부족" }}
        }}
        
        리뷰 내용:
        {" ".join(place_info['reviews'])}
        """
        
        # generation_config에서 response_mime_type을 제거하여 v1beta 강제 호출을 막음
        response = model.generate_content(prompt)
        
        # 텍스트에서 JSON 추출
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        ai_data = json.loads(match.group())
        
        final_result = {**ai_data, "name": place_info['name'], "address": place_info['address'], "rating": place_info['rating']}
        cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
        save_cache(cache)
        return final_result
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
