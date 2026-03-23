from typing import List
from playwright.sync_api import sync_playwright
import time

def search_kakao_places(query: str):
    print(f"\n[크롤러] '{query}'로 실제 지점 리스트 검색 중...")
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"https://map.kakao.com/?q={query}")
        time.sleep(2) 

        items = page.query_selector_all(".PlaceItem")
        for item in items[:5]:
            name_el = item.query_selector(".link_name")
            addr_el = item.query_selector(".addr")
            moreview_el = item.query_selector(".moreview") 

            # 이름, 주소와 함께 '고유 URL(href)'을 같이 뽑아옵니다!
            if name_el and addr_el and moreview_el:
                results.append({
                    "place_name": name_el.inner_text(),
                    "address_name": addr_el.inner_text(),
                    "place_url": moreview_el.get_attribute("href")
                })
        browser.close()
    return results
def scrape_kakao_reviews(place_url: str) -> List[str]:
    reviews = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()
        
        review_direct_url = f"{place_url.split('#')[0]}#review"
        print(f"\n[크롤러] 치트키 주소로 다이렉트 워프: {review_direct_url}")
        
        page.goto(review_direct_url)
        time.sleep(3) 
        
        try:
            print("[크롤러] 사람처럼 마우스 휠을 내립니다 (드르륵~ 드르륵~)")
            for _ in range(3):
                page.mouse.wheel(0, 800)
                time.sleep(1)
            
            # 🚨 [무적 모드] 클래스 이름표 버림! "후기"나 "별점" 글자가 뜰 때까지 대기
            print("[크롤러] 이름표(클래스명) 버렸습니다! 진짜 '글자' 자체를 스캔 중...")
            page.wait_for_function(
                "() => document.body.innerText.includes('유용한 순') || document.body.innerText.includes('별점평균') || document.body.innerText.includes('메뉴 더보기')", 
                timeout=7000
            )
            
            # 더보기 버튼 누르기 (이것도 텍스트로 찾아서 클릭)
            try:
                more_buttons = page.get_by_text("더보기", exact=True)
                for i in range(more_buttons.count()):
                    more_buttons.nth(i).click(timeout=1000)
                    time.sleep(0.5)
            except:
                pass 

            # 🚨 [핵심] Javascript를 주입해서 날짜(YYYY.MM.DD)가 포함된 덩어리만 통째로 뜯어옴!
            extracted_reviews = page.evaluate("""() => {
                const lis = Array.from(document.querySelectorAll('li'));
                // 정규식으로 '2024.03.06.' 같은 날짜가 있는 li 태그만 필터링
                const reviewLis = lis.filter(li => /\\d{4}\\.\\d{2}\\.\\d{2}\\./.test(li.innerText));
                return reviewLis.map(li => li.innerText.trim());
            }""")
            
            # 플랜 A: 날짜가 있는 리뷰 덩어리 낚아채기 성공
            if extracted_reviews:
                print(f"[크롤러] 빙고! 날것의 리뷰 덩어리 {len(extracted_reviews)}개를 성공적으로 낚아챘습니다!")
                for text in extracted_reviews[:10]:
                    clean_text = " ".join(text.split('\n')) # 보기 좋게 한 줄로 합침
                    reviews.append(clean_text)
            
            # 플랜 B: 구조가 너무 특이해서 못 찾으면 화면 전체 글자를 강제로 긁어서 AI한테 던짐!
            else:
                print("[크롤러] 플랜 B: 리스트를 못 찾아서 화면 전체 텍스트를 강제로 긁어옵니다! (AI가 알아서 해독할 겁니다)")
                all_text = page.evaluate("() => document.body.innerText")
                reviews.append(all_text[:5000]) # 글자가 너무 길면 터지니까 5000자만 자름
                
        except Exception as e:
            print(f"[크롤러] 최후의 수단도 에러 발생: {e}")
        
        browser.close()
        
    return reviews