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

def get_dynamic_prompt(lang, place_info):
    if lang == "en":
        # 영어 모드: 이름과 주소도 영어로 번역하도록 지시 추가
        instruction = "You are a 'Global Restaurant Risk Profiler AI'. TRANSLATE the restaurant name and address into English naturally."
        guidelines = """
        [Guidelines]
        1. Volume Check: 1,000+ reviews & 4.0+ rating = 'Landmark'.
        2. Mine Detection: Alert for hygiene, rudeness, or scams.
        3. Translation: You MUST translate the provided 'Name' and 'Address' into English.
        4. Response: Answer EVERYTHING in English.
        """
        json_format = """
        {
            "translatedName": "Name in English",
            "translatedAddress": "Address in English",
            "realScore": 1.0~5.0,
            "aiSummary": "Summary in English",
            "details": { "taste": "1~5/Insufficient Data", "value": "1~5/Insufficient Data", "service": "1~5/Insufficient Data", "time": "1~5/Insufficient Data", "hygiene": "1~5/Insufficient Data" }
        }
        """
    else:
        # 한국어 모드: 원래 데이터 유지
        instruction = "당신은 식당의 실체를 파헤치는 '글로벌 리스크 프로파일러 AI'입니다."
        guidelines = "모든 답변을 한국어로 작성하고, 이름과 주소는 원문 그대로 유지하세요."
        json_format = """
        {
            "translatedName": "가게 이름",
            "translatedAddress": "가게 주소",
            "realScore": 1.0~5.0,
            "aiSummary": "한국어 요약",
            "details": { "taste": "1~5/데이터 부족", "value": "1~5/데이터 부족", "service": "1~5/데이터 부족", "time": "1~5/데이터 부족", "hygiene": "1~5/데이터 부족" }
        }
        """

    return f"""
    {instruction}
    {guidelines}
    Return strictly in this JSON format:
    {json_format}

    Input Data: Name: {place_info['name']}, Address: {place_info['address']}
    Reviews: {" ".join(place_info['reviews'])}
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
            model = genai.GenerativeModel(model_name)
            prompt = get_dynamic_prompt(lang, place_info)
            response = model.generate_content(prompt)
            
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group())
                
                # 💡 [핵심] AI가 번역해준 이름을 우선 사용하고, 없으면 원래 이름 사용
                final_result = {
                    **ai_data, 
                    "name": ai_data.get("translatedName") or place_info['name'], 
                    "address": ai_data.get("translatedAddress") or place_info['address'], 
                    "rating": place_info['rating']
                }
                
                cache[cache_key] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
                save_cache(cache)
                return final_result
        except Exception as e:
            continue

    raise HTTPException(status_code=500, detail="분석 실패")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
