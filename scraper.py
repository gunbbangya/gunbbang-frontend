import os
import requests

def search_and_get_reviews(query: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    print(f"\n[🌐 글로벌 구글 검색] '{query}' 검색 및 리뷰 추출 중...")

    # 1. 식당 찾기 (Place Search)
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_params = {
        "query": query,
        "key": api_key,
        "language": "ko" # 한국어 리뷰 우선, 없으면 현지어
    }
    
    search_res = requests.get(search_url, params=search_params).json()
    
    if not search_res.get("results"):
        print("🚨 [CCTV] 구글에서 해당 식당을 찾을 수 없습니다.")
        return None

    # 가장 정확한 첫 번째 검색 결과 사용
    place_data = search_res["results"][0]
    place_id = place_data["place_id"]
    
    # 2. 식당 상세 정보 및 리뷰 가져오기 (Place Details)
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        "place_id": place_id,
        "fields": "name,formatted_address,rating,reviews",
        "key": api_key,
        "language": "ko"
    }
    
    details_res = requests.get(details_url, params=details_params).json()
    result = details_res.get("result", {})

    # 리뷰 데이터 정리
    raw_reviews = result.get("reviews", [])
    clean_reviews = [r.get("text", "") for r in raw_reviews if r.get("text")]

    print(f"✅ [CCTV] '{result.get('name')}' 리뷰 {len(clean_reviews)}개 확보 성공!")

    return {
        "name": result.get("name"),
        "address": result.get("formatted_address"),
        "rating": result.get("rating"),
        "reviews": clean_reviews
    }