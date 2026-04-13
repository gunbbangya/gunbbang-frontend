import os
import time
import random
import requests
from pymongo import MongoClient  # 💡 몽고DB 도구 추가!
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# ⚙️ 1. 환경 설정 및 API 연결
# ==========================================
load_dotenv()
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gourmet_model = genai.GenerativeModel('models/gemini-1.5-flash')

# 💡 MongoDB 연결 설정
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("🚨 에러: .env 파일에 MONGO_URI가 없습니다!")
    exit()

client = MongoClient(MONGO_URI)
db = client["jjin_view_db"]       # 데이터베이스 이름 생성
collection = db["places_cache"]   # 데이터를 담을 테이블(컬렉션) 이름 생성

# 타겟 지역 및 키워드 설정
TARGET_REGIONS = ["강남역 맛집", "성수동 맛집", "명동 맛집"]

# ==========================================
# 🕷️ 2. 수집 기능 (카카오 API + 숨겨진 리뷰 API)
# ==========================================
def search_target_places(query: str):
    print(f"\n[🔍 탐색] '{query}' 식당 리스트 수집 중...")
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query, "size": 15}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200: return []
    return response.json().get("documents", [])

def get_kakao_reviews_stealth(place_id: str, place_name: str):
    api_url = f"https://place.map.kakao.com/main/v/{place_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Referer": f"https://place.map.kakao.com/{place_id}" 
    }
    
    try:
        res = requests.get(api_url, headers=headers)
        if res.status_code != 200: return []
        
        data = res.json()
        reviews = []
        comment_list = data.get("comment", {}).get("list", [])
        for comment in comment_list:
            content = comment.get("contents")
            point = comment.get("point", 0)
            if content:
                reviews.append(f"별점: {point}점 - 내용: {content}")
        return reviews
    except:
        return []

# ==========================================
# 🤖 3. AI 판독 기능
# ==========================================
def analyze_with_ai(place_name: str, reviews: list):
    reviews_text = "\n---\n".join(reviews[:20])
    
    prompt = f"""
    당신은 광고성 리뷰를 걸러내는 '냉혹한 미식 프로파일러'입니다.
    식당명: {place_name}
    
    [엄격한 채점 기준]
    1. 기본 점수 3.0점 시작. 
    2. '서비스 받았어요', '이벤트' 등의 문구가 있다면 eventProbability를 대폭 올리고 realScore는 2.9점 이하로 강제 고정.
    3. 구체적인 단점 지적 시 가중치 2배 부여하여 감점.
    
    반드시 아래 JSON 형식으로 반환하세요:
    {{
        "realScore": 1.0~5.0,
        "eventProbability": 0~100,
        "aiSummary": "리뷰 이벤트 정황을 포함한 냉정한 분석",
        "details": {{ "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5, "hygiene": 1~5 }}
    }}
    
    리뷰 데이터:
    {reviews_text}
    """
    try:
        response = gourmet_model.generate_content(prompt)
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"🚨 AI 판독 실패 ({place_name}): {e}")
        return None

# ==========================================
# 🚀 4. 메인 자동화 파이프라인 (클라우드 DB 연동)
# ==========================================
def start_database_building():
    total_processed = 0
    
    for region in TARGET_REGIONS:
        places = search_target_places(region)
        
        for place in places:
            place_id = place["id"]
            place_name = place["place_name"]
            
            # 💡 [핵심] 클라우드 DB에 이미 이 식당 정보가 있는지 확인
            existing_place = collection.find_one({"_id": place_id})
            if existing_place:
                print(f"⏩ 스킵: '{place_name}' (이미 클라우드 DB에 존재함)")
                continue
                
            print(f"\n[{total_processed+1}] 🎯 '{place_name}' 수집 및 분석 시작...")
            
            reviews = get_kakao_reviews_stealth(place_id, place_name)
            if len(reviews) < 3:
                print(f"   ↪ 리뷰 부족. 건너뜁니다.")
                continue
                
            ai_result = analyze_with_ai(place_name, reviews)
            if not ai_result:
                continue
                
            # 💡 [핵심] 클라우드 DB에 저장 (JSON 파일 대신)
            document = {
                "_id": place_id,  # 몽고DB의 고유 인식표
                "name": place_name,
                "address": place.get("road_address_name") or place.get("address_name"),
                "category": place.get("category_name", ""),
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "analysis": ai_result
            }
            # 데이터 삽입 (upsert=True: 없으면 넣고, 있으면 업데이트)
            collection.update_one({"_id": place_id}, {"$set": document}, upsert=True)
            
            print(f"   ✅ 클라우드 저장 완료! (realScore: {ai_result.get('realScore')} / 조작확률: {ai_result.get('eventProbability')}%)")
            
            total_processed += 1
            
            sleep_time = random.uniform(8, 18)
            print(f"   💤 봇 탐지 방지: {sleep_time:.1f}초 대기 중...")
            time.sleep(sleep_time)

if __name__ == "__main__":
    print("==============================================")
    print("☁️ 찐-뷰 클라우드 DB 수집 공장 가동을 시작합니다.")
    print("==============================================")
    start_database_building()