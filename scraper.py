import os
import requests

def search_and_get_reviews(query: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("🚨 [에러] GOOGLE_API_KEY 누락")
        return None

    # 1. 식당 검색
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": api_key, "language": "ko"}
    
    try:
        res = requests.get(search_url, params=params).json()
        if not res.get("results"):
            print(f"🚨 [결과 없음] '{query}' 검색 결과가 없습니다.")
            return None

        place = res["results"][0]
        place_id = place["place_id"]
        
        # 2. 상세 정보 추출 (user_ratings_total 필드 추가!)
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        d_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,rating,user_ratings_total,reviews",
            "key": api_key,
            "language": "ko"
        }
        
        d_res = requests.get(details_url, params=d_params).json()
        result = d_res.get("result", {})
        
        # 리뷰 텍스트 추출
        reviews = [r.get("text", "") for r in result.get("reviews", []) if r.get("text")]

        print(f"✅ [구글 데이터 확보] {result.get('name')} (평점: {result.get('rating')}, 리뷰수: {result.get('user_ratings_total')})")

        return {
            "name": result.get("name", query),
            "address": result.get("formatted_address", ""),
            "rating": result.get("rating", 0),
            "user_ratings_total": result.get("user_ratings_total", 0), # 이 데이터가 필수!
            "reviews": reviews
        }
    except Exception as e:
        print(f"🚨 scraper.py 에러: {e}")
        return None
