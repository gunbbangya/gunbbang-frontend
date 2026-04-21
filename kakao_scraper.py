import os
import time
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# 💡 [수정됨] 구글 주소(google_address)를 같이 받아서 비교합니다!
def get_kakao_place_id(place_name: str, google_address: str):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        # 동명이인 가게를 찾기 위해 size를 10으로 넉넉히 가져옵니다
        res = requests.get(url, headers=headers, params={"query": place_name, "size": 10})
        if res.status_code == 200 and res.json().get("documents"):
            docs = res.json()["documents"]
            
            if not google_address:
                return docs[0]["id"]

            # 구글 주소를 공백 기준으로 쪼갭니다 (예: ['경기', '수원시', '팔달구', ...])
            g_words = set(google_address.split())

            for doc in docs:
                k_addr1 = set(doc.get("address_name", "").split())
                k_addr2 = set(doc.get("road_address_name", "").split())
                
                # 구글 주소와 카카오 주소에서 단어가 2개 이상 겹치면(예: 수원시, 팔달구) 동일 가게로 판단!
                if len(g_words & k_addr1) >= 2 or len(g_words & k_addr2) >= 2:
                    print(f"🎯 [카카오 매칭 성공] {place_name} ({doc.get('address_name')})")
                    return doc["id"]

            # 주소 매칭에 실패하면 어쩔 수 없이 첫 번째 결과 반환
            print(f"⚠️ [카카오 매칭 경고] '{place_name}' 정확한 주소를 못 찾아 첫 번째 결과로 진행합니다.")
            return docs[0]["id"]
            
    except Exception as e:
        print(f"🚨 카카오 ID 검색 실패: {e}")
    return None

# 2. 플레이라이트로 카카오 리뷰 25개 긁어오는 함수
def get_deep_kakao_reviews(place_id: str):
    reviews = []
    place_url = f"https://place.map.kakao.com/{place_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()
        
        review_direct_url = f"{place_url}#review"
        print(f"🕵️‍♂️ [카카오 크롤러] 출동: {review_direct_url}")
        
        try:
            page.goto(review_direct_url)
            time.sleep(3) 
            
            for _ in range(3):
                page.mouse.wheel(0, 800)
                time.sleep(1)
            
            try:
                more_buttons = page.get_by_text("더보기", exact=True)
                for i in range(more_buttons.count()):
                    more_buttons.nth(i).click(timeout=1000)
                    time.sleep(0.5)
            except: pass 

            extracted_reviews = page.evaluate("""() => {
                const lis = Array.from(document.querySelectorAll('li'));
                const reviewLis = lis.filter(li => /\\d{4}\\.\\d{2}\\.\\d{2}\\./.test(li.innerText));
                return reviewLis.map(li => li.innerText.trim());
            }""")
            
            if extracted_reviews:
                # 💡 심층 분석을 위해 15개 -> 25개로 늘렸습니다!
                for text in extracted_reviews[:25]: 
                    clean_text = " ".join(text.split('\n')) 
                    reviews.append(clean_text)
            else:
                all_text = page.evaluate("() => document.body.innerText")
                reviews.append(all_text[:5000]) 
                
        except Exception as e:
            print(f"🚨 [카카오 크롤러] 에러: {e}")
        finally:
            browser.close()
            
    return reviews