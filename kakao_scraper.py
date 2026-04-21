import os
import time
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# 1. 가게 이름으로 카카오맵 고유 ID(place_id) 알아내는 함수
def get_kakao_place_id(place_name: str):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, params={"query": place_name, "size": 1})
        if res.status_code == 200 and res.json().get("documents"):
            return res.json()["documents"][0]["id"]
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