import os
import time
import random
import requests
import json
import re
from pymongo import MongoClient
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright  # 💡 사용자님의 무기 장착!

# ==========================================
# ⚙️ 1. 환경 설정 및 API 연결
# ==========================================
load_dotenv()
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["jjin_view_db"]
collection = db["places_cache"]

# ==========================================
# 🗺️ 2. 강남구 격자 (Grid) 스캔 (광속 API 유지)
# ==========================================
LAT_START, LAT_END = 37.4600, 37.5400  
LON_START, LON_END = 127.0100, 127.1200 
STEP = 0.001  

def get_places_from_grid(lat, lon):
    places = []
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    
    for page in range(1, 4):
        params = {
            "category_group_code": "FD6",
            "x": str(lon), "y": str(lat),
            "radius": 100,      
            "sort": "distance", 
            "page": page,
            "size": 15
        }
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                places.extend(data.get("documents", []))
                if data.get("meta", {}).get("is_end"): 
                    break
            time.sleep(0.3)
        except Exception as e:
            break
    return places

# ==========================================
# 🕷️ 3. 카카오 딥 크롤러 (사용자님 Playwright 원본 이식!)
# ==========================================
def get_deep_kakao_reviews(place_id: str):
    reviews = []
    place_url = f"https://place.map.kakao.com/{place_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()
        
        review_direct_url = f"{place_url}#review"
        print(f"  [크롤러] 치트키 주소로 다이렉트 워프: {review_direct_url}")
        
        try:
            page.goto(review_direct_url)
            time.sleep(3) 
            
            print("  [크롤러] 사람처럼 마우스 휠을 내립니다 (드르륵~ 드르륵~)")
            for _ in range(3):
                page.mouse.wheel(0, 800)
                time.sleep(1)
            
            print("  [크롤러] 이름표(클래스명) 버렸습니다! 진짜 '글자' 자체를 스캔 중...")
            try:
                page.wait_for_function(
                    "() => document.body.innerText.includes('유용한 순') || document.body.innerText.includes('별점평균') || document.body.innerText.includes('메뉴 더보기')", 
                    timeout=7000
                )
            except:
                pass
            
            try:
                more_buttons = page.get_by_text("더보기", exact=True)
                for i in range(more_buttons.count()):
                    more_buttons.nth(i).click(timeout=1000)
                    time.sleep(0.5)
            except:
                pass 

            # 🚨 [사용자님 핵심 로직] Javascript 주입 (정규식 필터링)
            extracted_reviews = page.evaluate("""() => {
                const lis = Array.from(document.querySelectorAll('li'));
                // 정규식으로 '2024.03.06.' 같은 날짜가 있는 li 태그만 필터링
                const reviewLis = lis.filter(li => /\\d{4}\\.\\d{2}\\.\\d{2}\\./.test(li.innerText));
                return reviewLis.map(li => li.innerText.trim());
            }""")
            
            if extracted_reviews:
                print(f"  [크롤러] 빙고! 날것의 리뷰 덩어리 {len(extracted_reviews)}개를 성공적으로 낚아챘습니다!")
                for text in extracted_reviews[:15]: 
                    clean_text = " ".join(text.split('\n')) 
                    reviews.append(clean_text)
            else:
                print("  [크롤러] 플랜 B: 리스트를 못 찾아서 화면 전체 텍스트를 강제로 긁어옵니다! (AI가 알아서 해독할 겁니다)")
                all_text = page.evaluate("() => document.body.innerText")
                reviews.append(all_text[:5000]) 
                
        except Exception as e:
            print(f"  🚨 [크롤러] 최후의 수단도 에러 발생: {e}")
        
        finally:
            browser.close()
            
    return reviews


# ==========================================
# 🤖 4. AI 판독 (최신 2.5 flash 연쇄 호출 로직 적용)
# ==========================================
def analyze_with_ai(place_name: str, address: str, reviews: list):
    reviews_text = "\n".join(reviews)
    
    prompt = f"""
    당신은 광고성 리뷰를 걸러내고 조작된 평점을 파괴하는 '냉혹한 미식 프로파일러'입니다.

    [리뷰 이벤트 및 조작 패턴 감지]
    1. 핵심 키워드 감시: '서비스 받았어요', '이벤트 참여', '음료수 서비스', '사진 리뷰 약속' 등의 문구가 보이면 무조건 'eventProbability'를 높이세요.
    2. 맥락적 정황 포착: '이벤트'라는 직접적 단어가 없더라도, 음식(맛, 식감, 양)에 대한 구체적 묘사 없이 "사장님이 친절해요", "가게가 예뻐요" 등 부차적인 칭찬만 나열된 5점 리뷰는 보상형 리뷰일 확률이 매우 높으므로 'eventProbability'에 적극 반영하세요.
    3. 영혼 없는 5점: "맛있어요", "최고예요" 등 구체적인 설명 없이 이모티콘만 있거나 너무 짧은 5점 리뷰는 '리뷰 이벤트' 정황으로 간주합니다.
    4. 신뢰도 가중치: 사진이 없거나 짧은 5점보다, 단점을 구체적으로 지적한 1~3점 리뷰에 2배의 가중치를 두어 점수를 깎으세요.
    5. 'eventProbability' 산출: 0~100% 사이의 정수로, 리뷰 이벤트가 의심되는 정도를 계산하세요.

    [🔥 핵심: 리뷰어 성향(평점 신뢰도) 판별법]
    6. 제공된 리뷰 텍스트 안에서 각 유저의 '후기 개수'와 '평균별점' 정보를 반드시 찾아내어 분석하세요:
       - 깐깐한 미식가(평균 3.5 이하)가 5점을 주었다면 찐맛집일 확률이 높으므로 가중치를 대폭 높이세요.
       - 습관성 만점자(평균 4.8 이상)의 영혼 없는 5점이나, 악의적 테러범(평균 2.0 이하)의 무지성 1점은 철저히 무시하고 분석에서 배제하세요.

    [엄격한 채점 기준]
    1. 기본 점수: 3.0점. 4.0점 이상은 대한민국 상위 1% 식당에만 부여합니다.
    2. 점수 상한선: 'eventProbability'가 70% 이상이면 'realScore'는 무조건 2.9점 이하로 강제 고정합니다.
    3. 감점: 불친절/위생(-1.5점), 웨이팅/비쌈(-1.0점).
    
    Return strictly in this JSON format:
    {{
        "translatedName": "English Name of {place_name}",
        "realScore": 1.0~5.0,
        "eventProbability": 0~100,
        "aiSummary_ko": "리뷰 이벤트 정황과 리뷰어 신뢰도를 포함한 냉정한 한국어 한줄평",
        "aiSummary_en": "Critical English summary focusing on fake patterns, food quality, and reviewer reliability",
        "details": {{ "taste": 1~5, "value": 1~5, "service": 1~5, "time": 1~5, "hygiene": 1~5 }}
    }}

    Input Data: Name: {place_name}, Address: {address}
    Reviews: {reviews_text}
    """
    
    # 💡 [핵심] main.py에 있던 생존형 모델 찾기 로직!
    target_models = ['models/gemini-2.5-flash', 'models/gemini-2.0-flash', 'models/gemini-flash-latest']
    
    for model_name in target_models:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt)
            
            import re, json
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if not match: 
                continue 
            
            data = json.loads(match.group())
            
            analysis_ko = {
                "translatedName": data.get("translatedName", place_name),
                "translatedAddress": address,
                "realScore": data.get("realScore", 3.0),
                "eventProbability": data.get("eventProbability", 0),
                "aiSummary": data.get("aiSummary_ko", ""),
                "details": data.get("details", {})
            }
            
            analysis_en = {
                "translatedName": data.get("translatedName", place_name),
                "translatedAddress": "Leave empty",
                "realScore": data.get("realScore", 3.0),
                "eventProbability": data.get("eventProbability", 0),
                "aiSummary": data.get("aiSummary_en", ""),
                "details": data.get("details", {})
            }
            
            return analysis_ko, analysis_en
            
        except Exception as e:
            print(f"  ⚠️ [{model_name}] 모델 판독 실패: {e} -> 다음 모델로 재도전합니다.")
            continue 
            
    print("🚨 모든 AI 모델 판독에 실패했습니다.")
    return None, None

# ==========================================
# 🚀 5. 강남구 전체 전수조사 파이프라인 (최적화 완료)
# ==========================================
def run_grid_scanner():
    print("==============================================")
    print("🌐 [찐-뷰] 강남구 전체 격자 스캔 공장 가동! (Playwright 무적 모드)")
    print("==============================================")
    
    total_saved = 0
    curr_lat = LAT_START
    
    # 💡 [핵심 최적화 1] 이번 턴에 한 번이라도 건드린 식당 기억하기
    processed_ids = set()
    
    while curr_lat <= LAT_END:
        curr_lon = LON_START
        while curr_lon <= LON_END:
            print(f"\n📍 [스캔 중] 좌표: {curr_lat:.4f}, {curr_lon:.4f}")
            places = get_places_from_grid(curr_lat, curr_lon)
            
            for place in places:
                place_id = place["id"]
                place_name = place["place_name"]
                address = place.get("road_address_name") or place.get("address_name")
                
                # 1. 중복 체크 (세션 내)
                if place_id in processed_ids:
                    continue 
                processed_ids.add(place_id)
                    
                # 2. 중복 체크 (DB 내 - name 대신 더 정확한 place_id 사용)
                if collection.find_one({"place_id": place_id}):
                    continue 
                    
                print(f"🎯 발견: '{place_name}' (리뷰 추출 중...)")
                
                # 3. 딥 크롤링 (Playwright)
                reviews = get_deep_kakao_reviews(place_id)
                if len(reviews) < 5:
                    print(f"  ↪ '{place_name}' 유효 리뷰 부족({len(reviews)}개). 다음 실행 때까지 패스!")
                    continue
                
                # 4. 제미나이 분석
                analysis_ko, analysis_en = analyze_with_ai(place_name, address, reviews)
                
                # 🚨 [핵심 최적화 2] AI가 파업(한도 초과 등)하면 공장 강제 종료
                if not analysis_ko:
                    print("🚨 AI 판독 불능 (API 한도 초과 의심). 공장을 일시 정지합니다.")
                    print("내일 다시 실행하거나, 12시간 뒤에 켜주세요!")
                    return # 여기서 프로그램 종료!
                
                # 5. MongoDB 저장 
                document = {
                    "name": place_name, 
                    "place_id": place_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "address": address,
                    "analysis_ko": analysis_ko,
                    "analysis_en": analysis_en
                }
                collection.update_one({"place_id": place_id}, {"$set": document}, upsert=True)
                
                print(f"  ✅ DB 저장 완료! [평점: {analysis_ko.get('realScore')} / 조작확률: {analysis_ko.get('eventProbability')}%]")
                total_saved += 1
                
                # 봇 차단 방지 
                normal_sleep = random.uniform(6, 12)
                time.sleep(normal_sleep)

                if total_saved > 0 and total_saved % 100 == 0:
                    coffee_break = random.uniform(180, 300)
                    print(f"\n☕ [커피 브레이크] 100개 달성! {coffee_break/60:.1f}분 대기...\n")
                    time.sleep(coffee_break)
            
            curr_lon += STEP 
        curr_lat += STEP 

    print(f"\n🏁 강남구 전수조사 완료! 총 {total_saved}개 식당 영구 저장됨.")

if __name__ == "__main__":
    run_grid_scanner()