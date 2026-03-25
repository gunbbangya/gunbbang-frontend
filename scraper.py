import os
import requests
# hello
def search_kakao_places(query: str):
    print(f"\n[🚀 광속 API] '{query}' 검색 중...")
    
    kakao_api_key = os.getenv("KAKAO_API_KEY")
    if not kakao_api_key:
        print("🚨 에러: 카카오 API 키가 없습니다!")
        return []

    # 카카오 공식 로컬 API 호출
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {"query": query, "size": 5}

    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"카카오 API 검색 실패: {response.text}")
        return []

    data = response.json()
    results = []
    
    for item in data.get("documents", []):
        results.append({
            "place_name": item["place_name"],
            # 도로명 주소가 없으면 지번 주소 사용
            "address_name": item.get("road_address_name") or item.get("address_name"),
            "place_url": f"https://place.map.kakao.com/{item['id']}"
        })
        
    return results

def scrape_kakao_reviews(place_url: str):
    print(f"\n[🕵️‍♂️ 숨겨진 API] {place_url}에서 리뷰 데이터 직행 추출 중...")
    
    # URL에서 식당 고유 ID만 빼내기
    place_id = place_url.split("/")[-1].split("?")[0].split("#")[0]

    # 카카오맵이 내부적으로 쓰는 숨겨진 데이터 서버에 다이렉트 요청
    api_url = f"https://place.map.kakao.com/main/v/{place_id}"
    
    # 💡 1. 방문증(Referer) 추가!
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": place_url 
    }

    response = requests.get(api_url, headers=headers)
    
    # 💡 2. CCTV 설치: 카카오가 뭐라고 대답했는지 로그에 찍기
    print(f"🚨 [CCTV] 카카오 응답 코드: {response.status_code}")
    
    if response.status_code != 200:
        print(f"🚨 [CCTV] 카카오가 거절했습니다. 사유: {response.text[:200]}")
        return []

    data = response.json()
    reviews = []
    
    

    try:
        # 데이터 속에서 리뷰(comment)만 쏙 빼오기
        comment_list = data.get("comment", {}).get("list", [])
        for comment in comment_list:
            content = comment.get("contents")
            point = comment.get("point")
            if content:
                reviews.append(f"별점: {point}점 - 내용: {content}")
                
    except Exception as e:
        print(f"리뷰 추출 에러: {e}")

    return reviews
