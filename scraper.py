import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from scraper import search_and_get_reviews
import google.generativeai as genai
from dotenv import load_dotenv

# 환경 설정
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"
last_queries = {} # 422 방어용 비상 저장소

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 검색: 어제처럼 프론트가 바로 읽을 수 있는 리스트([]) 형식으로 반환
@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q # 프론트가 혹시라도 이름을 빼먹고 보낼 때를 대비

        result = search_and_get_reviews(q)
        if not result:
            return []

        # 프론트엔드 UI가 기대하는 카카오 API 형식의 '이름'들입니다.
        formatted_result = {
            "id": result["name"], 
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"], # 분석 시 이 값을 query로 씀
            "category_name": "식당",
            "phone": ""
        }
        
        # [ { ... } ] 리스트 형태로 반환 (어제 됐던 그 방식)
        return [formatted_result]
        
    except Exception as e:
        print(f"❌ 검색 서버 에러: {e}")
        return []

# 2. 분석: 프론트가 보낸 데이터가 조금 부족해도 찰떡같이 알아먹기
@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    
    try:
        data = await request.json()
    except:
        data = {}

    # 프론트가 보낼 수 있는 모든 필드를 다 뒤집니다.
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석 대상을 특정할 수 없습니다.")

    # 캐시 확인 로직
    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    # 실제 API 호출 및 AI 분석
    place_info = search_and_get_reviews(query)
    if not place_info:
        raise HTTPException(status_code=404, detail="식당 정보를 찾을 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    # 제미나이 AI 분석 (어제와 동일)
    prompt = f"식당명: {place_info['name']}\n명령: 리뷰를 분석해서 JSON만 반환해.\n리뷰:\n{reviews_text}"
    # ... (이후 분석 로직은 어제와 동일하므로 생략하거나 기존 로직 유지)
    # 파운더님 코드의 일관성을 위해 전체 구조 유지합니다.
    
    # [주의] 이 아래는 파운더님이 기존에 쓰시던 AI 모델 호출 코드를 그대로 넣으시면 됩니다.
    # 제가 앞서 드린 '전체 코드'의 AI 분석 부분과 동일합니다.
    
    # (코드 가독성을 위해 생략 없이 이어서 작성합니다)
    gourmet_model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
    response = gourmet_model.generate_content(prompt)
    ai_data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    
    final_result = {**ai_data, "name": place_info['name'], "address": place_info['address'], "rating": place_info['rating']}
    cache[query] = {"date": datetime.now().strftime("%Y-%m-%d"), "result": final_result}
    save_cache(cache)
    return final_result

# 캐시 관련 보조 함수
def load_cache():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(cache_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
