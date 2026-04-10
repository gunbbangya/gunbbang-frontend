import os
import requests

def search_and_get_reviews(query: str):
    """
    구글 Places API를 사용하여 식당 정보와 리뷰를 가져옵니다.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("🚨 [에러] GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return None

    print(f"\n[🌐 구글 API] '{query}' 검색 시작...")

    # 1. Place Search: 식당 검색하여 place_id 획득
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_params = {
        "query": query,
        "key": api_key,
        "language": "ko"
    }
    
    try:
        search_res = requests.get(search_url, params=search_params).json()
        if not search_res.get("results"):
            print("🚨 [결과 없음] 해당 검색어로 식당을 찾을 수 없습니다.")
            return None

        # 가장 관련성 높은 첫 번째 결과 사용
        place_data = search_res["results"][0]
        place_id = place_data["place_id"]
        
        # 2. Place Details: place_id를 이용해 리뷰와 상세 정보 가져오기
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,rating,reviews",
            "key": api_key,
            "language": "ko"
        }
        
        details_res = requests.get(details_url, params=details_params).json()
        result = details_res.get("result", {})

        # 리뷰 텍스트만 추출 (최대 5개 제공됨)
        raw_reviews = result.get("reviews", [])
        clean_reviews = [r.get("text", "") for r in raw_reviews if r.get("text")]

        print(f"✅ [성공] '{result.get('name')}' 데이터 및 리뷰 {len(clean_reviews)}개 확보!")

        return {
            "name": result.get("name", query),
            "address": result.get("formatted_address", "주소 정보 없음"),
            "rating": result.get("rating", 0),
            "reviews": clean_reviews
        }

    except Exception as e:
        print(f"🚨 [API 예외 발생] {e}")
        return None
