import os
import requests

def search_and_get_reviews(query: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    # API 키가 없는 경우 대비
    if not api_key:
        print("🚨 [에러] GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return None

    print(f"\n[🌐 구글 API] '{query}' 데이터 수집 시작...")

    # 1. Place Search (식당 찾기)
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_params = {
        "query": query,
        "key": api_key,
        "language": "ko"
    }
    
    try:
        search_res = requests.get(search_url, params=search_params).json()
        if not search_res.get("results"):
            print("🚨 [CCTV] 식당을 찾을 수 없습니다.")
            return None

        place_data = search_res["results"][0]
        place_id = place_data["place_id"]
        
        # 2. Place Details (리뷰 가져오기)
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,rating,reviews",
            "key": api_key,
            "language": "ko"
        }
        
        details_res = requests.get(details_url, params=details_params).json()
        result = details_res.get("result", {})

        raw_reviews = result.get("reviews", [])
        clean_reviews = [r.get("text", "") for r in raw_reviews if r.get("text")]

        print(f"✅ [CCTV] '{result.get('name')}' 리뷰 {len(clean_reviews)}개 확보 성공!")

        return {
            "name": result.get("name"),
            "address": result.get("formatted_address"),
            "rating": result.get("rating"),
            "reviews": clean_reviews
        }
    except Exception as e:
        print(f"🚨 API 호출 중 예외 발생: {e}")
        return None
