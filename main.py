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

# 💡 [핵심] 언어별 프롬프트를 생성하는 함수
def get_dynamic_prompt(lang, place_info):
    if lang == "en":
        # 영어 모드 프롬프트
        instruction = "You are a 'Global Restaurant Risk Profiler AI' specialized in detecting fake reviews and identifying hidden gems."
        guidelines = """
        [Analysis Guidelines]
        1. Volume Check: If 1,000+ reviews and 4.0+ rating, recognize as a 'Landmark'.
        2. Mine Detection: Immediate [DANGER] warning for mentions of hygiene, rudeness, or overpricing.
        3. Integrity: If data for a category (taste, value, etc.) is missing, mark as "Insufficient Data".
        4. No Marketing: Ignore generic marketing phrases.
        5. Response Language: You MUST answer strictly in ENGLISH.
        """
        json_format = """
        {
            "realScore": 1.0~5.0,
            "aiSummary": "Summary (Max 3 lines)",
            "details": { "taste": "1~5 or Insufficient Data", "value": "1~5 or Insufficient Data", "service": "1~5 or Insufficient Data", "time": "1~5 or Insufficient Data", "hygiene": "1~5 or Insufficient Data" }
        }
        """
    else:
        # 한국어 모드 프롬프트 (기존 로직 유지)
        instruction = "당신은 식당의 실체를 파헤치는 '글로벌 리스크 프로파일러 AI'입니다."
        guidelines = """
        [판독 지침]
        1. 볼륨 판독: 500개 이상/4.0점 이상이면 강력 추천. 1,000개 이상/3.5점 이상이면 랜드마크 맛집 인정.
        2. 지뢰 경고: 위생, 식중독, 불친절, 바가지 언급 시 즉시 [위험] 경고.
        3. 데이터 정직성: 근거 없으면 반드시 "데이터 부족" 표기.
        4. 응답 언어: 반드시 한국어로 답변하세요.
        """
        json_format = """
        {
            "realScore": 1.0~5.0,
            "aiSummary": "요약 (3줄 이내)",
            "details": { "taste": "1~5 또는 데이터 부족", "value": "1~5 또는 데이터 부족", "service": "1~5 또는 데이터 부족", "time": "1~5 또는 데이터 부족", "hygiene": "1~5 또는 데이터 부족" }
        }
        """

    return f"""
    {instruction}
    {guidelines}

    Return strictly in this JSON format:
    {json_format}

    Restaurant Info: {place_info['name']} (Rating: {place_info['rating']})
    Reviews to analyze:
    {" ".join(place_info['reviews'])}
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
    # 💡 캐시 키에 언어 정보 포함 (한/영 결과가 섞이지 않게 함)
    cache_key = f"{query}_{lang}"
    
    if cache_key in cache:
        cached_item = cache[cache_key]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=30):
            return cached_item["result"]

    place_info = search_and_get_reviews(query)
    if not place_info: raise HTTPException(status_code=404)

    target_models = ['models/gemini-2.5-flash', 'models/gemini-2.0-flash', 'models/gemini-flash-latest']
    
    for model_name in target_models:
        try:
            print(f"🚀 {model_name} 모델로 {lang} 모드 분석 시작...")
            model = genai.GenerativeModel(model_name)
            
            # 💡 여기서 동적 프롬프트 호출
            prompt = get_dynamic_prompt(lang, place_info)
            
            response = model.generate_content(prompt)
            
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group())
                final_result = {
                    **ai_data, 
                    "name": place_info['name'], 
                    "address": place_info['address'], 
                    "rating": place_info['rating']
                }
                cache[cache_key] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
                save_cache(cache)
                return final_result
        except Exception as e:
            print(f"⚠️ {model_name} 실패: {e}")
            continue

    raise HTTPException(status_code=500, detail="2026년형 AI 모델 연결에 실패했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
