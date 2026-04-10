import os
import requests

def search_and_get_reviews(query: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("🚨 [에러] GOOGLE_API_KEY가 없습니다.")
        return None

    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_params = {
        "query": query,
        "key": api_key,
        "language": "ko"
    }
    
    try:
        search_res = requests.get(search_url, params=search_params).json()
        if not search_res.get("results"):
            return None

        place_data = search_res["results"][0]
        place_id = place_data["place_id"]
        
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

        return {
            "name": result.get("name"),
            "address": result.get("formatted_address"),
            "rating": result.get("rating"),
            "reviews": clean_reviews
        }
    except Exception as e:
        print(f"🚨 API 에러: {e}")
        return None
