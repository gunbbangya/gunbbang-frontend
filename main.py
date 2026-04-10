import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
# scraper.py에서 함수를 가져옵니다. (scraper.py에는 import main이 없어야 함)
from scraper import search_and_get_reviews 
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 설정 및 API 로드
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DB_FILE = "analysis_cache.json"

# 💡 [핵심] 프론트엔드가 이름을 안 보낼 때를 대비해 마지막 검색어를 IP별로 저장
last_queries = {}

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 캐시 관리 함수
def load_cache():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

# ---------------------------------------------------------
# [기능 1] 검색 엔드포인트: 어제 밤에 성공했던 '순수 리스트' 형식
# ---------------------------------------------------------
@app.get("/api/search")
def search_places(q: str, request: Request):
    global last_queries
    try:
        client_ip = request.client.host
        last_queries[client_ip] = q  # 검색어를 메모리에 저장 (분석 시 사용)

        # scraper.py의 구글 API 호출 함수 실행
        result = search_and_get_reviews(q)
        
        if not result:
            return []

        # 💡 [필독] 프론트엔드 UI가 목록을 그릴 때 필요한 '이름표'를 어제 규격으로 맞춤
        formatted_result = {
            "id": result["name"],
            "place_name": result["name"],
            "address_name": result["address"],
            "road_address_name": result["address"],
            "place_url": result["name"], # 클릭 시 분석 요청 query로 전달됨
            "category_name": "음식점 > 식당",
            "phone": "Google 제공"
        }
        
        # 어제처럼 [ { ... } ] 형태의 배열로 반환
        return [formatted_result]
        
    except Exception as e:
        print(f"❌ 검색 에러 발생: {e}")
        return []

# ---------------------------------------------------------
# [기능 2] 분석 엔드포인트: 422 에러 방어 및 AI 분석
# ---------------------------------------------------------
@app.post("/api/analyze")
async def analyze_place(request: Request):
    global last_queries
    client_ip = request.client.host
    
    try:
        data = await request.json()
    except:
        data = {}

    # 💡 프론트가 data를 안 보내더라도 last_queries에서 이름을 가져와 422 에러 방지
    query = data.get("query") or data.get("id") or data.get("place_name") or last_queries.get(client_ip)
    lang = data.get("lang") or "ko"

    if not query:
        raise HTTPException(status_code=422, detail="분석할 식당 이름을 찾을 수 없습니다.")

    # 캐시 확인
    cache = load_cache()
    if query in cache:
        cached_item = cache[query]
        if datetime.now() - datetime.strptime(cached_item["date"], "%Y-%m-%d") < timedelta(days=7):
            return cached_item["result"]

    # 구글 API로 리뷰 다시 가져오기
    place_info = search_and_get_reviews(query)
    if not place_info or not place_info.get('reviews'):
        raise HTTPException(status_code=404, detail="리뷰 데이터를 찾을 수 없습니다.")

    reviews_text = "\n---\n".join(place_info['reviews'])
    
    try:
        # AI 모델 호출 (Gemini 1.5 Flash)
        gourmet_model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={"response_mime_type": "application/json"}
        )
        
        prompt = f"""
        식당명: {place_info['name']}
        아래 리뷰들을 분석해서 광고를 제외한 진짜 평점을 매기고 요약해줘.
        결과는 반드시 '{lang}' 언어로, JSON 형식으로만 답변해.
        
        리뷰 데이터:
        {reviews_text}
        """
        
        response = gourmet_model.generate_content(prompt)
        
        # JSON 세탁 및 로드
        ai_raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(ai_raw)
        
        final_result = {
            **ai_data,
            "name": place_info['name'],
            "address": place_info['address'],
            "rating": place_info['rating']
        }

        # 캐시 저장
        cache[query] = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "result": final_result
        }
        save_cache(cache)
        
        return final_result
        
    except Exception as e:
        print(f"❌ AI 분석 에러: {e}")
        raise HTTPException(status_code=500, detail="AI 분석 중 오류가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    # Render 배포 환경에서는 호스트와 포트 설정이 중요합니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)
