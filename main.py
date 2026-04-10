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

# 파운더님의 '지뢰 탐지' 철학을 2026년형 모델에 맞게 주입
analysis_prompt_base = """
당신은 식당의 실체를 파헤치는 '글로벌 리스크 프로파일러 AI'입니다. 

[판독 지침]
- 1,000개 이상/3.5점 이상: 랜드마크 맛집 인정.
- 위생, 불친절, 바가지 언급 시 즉시 [위험] 경고.
- 정보가 없는 항목은 반드시 "데이터 부족"으로 표기.

반드시 아래 JSON 형식으로만 응답하세요:
{
    "realScore": 1.0~5.0,
    "aiSummary": "요약",
    "details": { "taste": "1~5/데이터 부족", "value": "1~5/데이터 부족", "service": "1~5/데이터 부족", "time": "1~5/데이터 부족", "hygiene": "1~5/데이터 부족" }
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
        
        # 💡 [목록 복구] 프론트엔드가 어떤 키를 찾든 뜰 수 있게 융단폭격 맵핑
        return [{
            "id": result.get("name"),
            "place_name": result.get("name"),
            "name": result.get("name"),
            "address_name": result.get("address"),
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

    # 💡 [필살기] 로그에서 확인된 2026년형 모델들로 순차적 시도
    # 'models/'를 붙여서 경로를 확실히 지정합니다.
    target_models = ['models/gemini-2.5-flash', 'models/gemini-2.0-flash', 'models/gemini-flash-latest']
    
    for model_name in target_models:
        try:
            print(f"🚀 {model_name} 모델로 분석 시도 중...")
            model = genai.GenerativeModel(model_name)
            
            prompt = f"{analysis_prompt_base}\n\n식당: {place_info['name']}\n리뷰: {' '.join(place_info['reviews'])}"
            
            # response_mime_type을 빼고 표준 텍스트로 요청하여 v1beta 에러를 원천 차단
            response = model.generate_content(prompt)
            
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group())
                final_result = {**ai_data, "name": place_info['name'], "address": place_info['address'], "rating": place_info['rating']}
                cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
                save_cache(cache)
                return final_result
        except Exception as e:
            print(f"⚠️ {model_name} 실패: {e}")
            continue

    raise HTTPException(status_code=500, detail="2026년형 AI 모델 연결에 실패했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
