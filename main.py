import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape_kakao_reviews, search_kakao_places
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 환경 설정 및 API 키 장착
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. 캐시 파일 경로 설정
DB_FILE = "analysis_cache.json"

# =====================================================================
# 🧠 AI 시스템 지침 (박제)
# =====================================================================
system_prompt = """
당신은 카카오맵 리뷰의 진실을 파헤치는 '극강의 깐깐함을 자랑하는 데이터 프로파일러 AI'입니다.
단순히 리뷰 글귀만 보지 말고, 반드시 '리뷰어의 성향 데이터(레벨, 후기 수, 별점평균)'를 분석하여 가중치를 다르게 적용하세요.

[🔍 찐-뷰 핵심 알고리즘 (리뷰어 신뢰도 판별법)]
1. 깐깐한 미식가 우대: 리뷰어의 '별점평균'이 3점대 중반 이하로 깐깐한데, 이 가게에 높은 '별점'을 주었다면 엄청난 가산점을 부여하세요.
2. 보살의 분노: 리뷰어의 '별점평균'이 4.5 이상으로 후한데, 이 가게에 1~2점을 주었다면 치명적인 감점을 부여하세요.
3. 습관성 리뷰어 필터링: '별점평균'이 4.8 이상인데 5점을 주거나(리뷰 이벤트 의심), '별점평균'이 2.0 이하인데 1점을 주는(블랙컨슈머) 리뷰는 신뢰도를 대폭 깎아서 무시하세요.
4. 고인물 우대: '레벨'이 높고 '후기 수'가 많은 유저의 리뷰를, 신규 깡통 계정보다 훨씬 중요하게 반영하세요.
5. 내용 분석: 별점과 무관하게 글 내용에서 구체적인 칭찬/불만(예: "연어가 블럭같다", "알바생이 불친절하다")이 있다면 팩트로 간주하세요.

[🚨 엄격한 최종 평점(realScore) 기준]
위 알고리즘을 거친 진짜 평가를 바탕으로, 아래 절대 기준에 맞춰 점수를 매기세요.
- 4.0 ~ 5.0 : 전국구 인생 맛집 (완벽에 가까운 맛과 서비스, 어지간해선 주지 않음)
- 3.0 ~ 3.9 : 정말 훌륭한 찐 맛집 (누구에게나 자신 있게 추천할 수 있는 곳)
- 2.5 ~ 2.9 : 괜찮은 맛집 (실패하지 않고 기분 좋게 한 끼 먹을 수 있는 곳)
- 2.0 ~ 2.4 : 평범한 식당 (굳이 찾아갈 이유는 없는 평타 수준)
- 1.0 ~ 1.9 : 최악의 식당 (위생 불량, 불친절 등 절대 피해야 할 곳)

[출력 형식]
반드시 아래의 JSON 형식으로만 답변을 반환해 주세요. (큰따옴표 문법을 반드시 지키세요!)
{
    "realScore": 1.0에서 5.0 사이의 소수점 한 자리 숫자 (프로파일링을 거친 진짜 평점),
    "aiSummary": "거짓/이벤트 리뷰를 제외하고, 신뢰도 높은 리뷰어들이 꼽은 진짜 장단점을 종합한 3줄 요약평",
    "details": {
        "taste": 1에서 5 사이의 정수,
        "value": 1에서 5 사이의 정수,
        "service": 1에서 5 사이의 정수,
        "time": 1에서 5 사이의 정수
    }
}
"""

gourmet_model = genai.GenerativeModel(
    'gemini-2.5-flash',
    system_instruction=system_prompt,
    generation_config={"response_mime_type": "application/json"}
)

# =====================================================================
# 📂 데이터베이스(캐시) 관리 함수들
# =====================================================================
def load_cache():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_cache(cache_data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

# =====================================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    query: str

@app.get("/api/search")
def search_places(q: str):
    try:
        results = search_kakao_places(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail="검색 중 에러가 발생했습니다.")

@app.post("/api/analyze")
def analyze_place(request: AnalyzeRequest):
    # 🚨 URL 꼬리표 자르기
    raw_url = request.query
    place_url = raw_url.split('#')[0].split('?')[0]
    
    # --- 🕵️‍♂️ [1단계: 캐시 확인] ---
    cache = load_cache()
    if place_url in cache:
        cached_item = cache[place_url]
        analysis_date = datetime.strptime(cached_item["date"], "%Y-%m-%d")
        
        if datetime.now() - analysis_date < timedelta(days=7):
            print(f"⚡ [캐시 적중] '{place_url}' - 신선한 데이터 발견! 즉시 응답합니다.")
            return cached_item["result"]
        else:
            print(f"⏰ [캐시 만료] '{place_url}' - 7일이 지나서 다시 분석합니다.")

    # --- 🕷️ [2단계: 크롤링 진행] ---
    print(f"\n[서버] '{place_url}' 신규/재분석 시작!")
    reviews = scrape_kakao_reviews(place_url)

    if not reviews or len(reviews) < 3:
        raise HTTPException(status_code=404, detail="리뷰 데이터가 부족하여 판독할 수 없습니다.")

    # --- 🤖 [3단계: AI 분석 진행] ---
    print("[서버] 구글 Gemini 분석 중...")
    reviews_text = "\n---\n".join(reviews[:30]) 
    
    try:
        response = gourmet_model.generate_content(f"다음 리뷰들을 분석해 줘:\n{reviews_text}")
        
        # 1. 제미나이 날것 텍스트 가져오기 및 마크다운 세탁
        raw_text = response.text
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
            
        cleaned_text = cleaned_text.strip() 
        
        # 🚨 [CCTV 추가] 파싱 전에 무조건 날것 먼저 출력!
        print(f"\n[서버] 🤖 제미나이 날것의 답변:\n{cleaned_text}\n")
        
        # 🚨 [철벽 방어막] 파싱 에러 나도 안 죽게 try-except로 묶기
        try:
            ai_data = json.loads(cleaned_text)
        except json.JSONDecodeError as json_err:
            print(f"🚨 [서버] JSON 파싱 실패! 제미나이가 문법을 틀렸습니다: {json_err}")
            # 서버 안 죽게 가짜 데이터로 땜빵
            ai_data = {
                "realScore": 0,
                "aiSummary": f"AI가 분석 중 문법 오류를 냈습니다. 다시 시도해 주세요. (에러: {json_err})",
                "details": { "taste": 0, "value": 0, "service": 0, "time": 0 }
            }
        
        # --- 💾 [4단계: 결과 저장] ---
        cache[place_url] = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "result": ai_data
        }
        
        save_cache(cache)
        
        print(f"[서버] 분석 완료 및 캐시 저장 완료!")
        return ai_data
        
    except Exception as e:
        print(f"[서버] Gemini 연동 에러: {e}")
        raise HTTPException(status_code=500, detail="AI 연동 중 알 수 없는 에러가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)