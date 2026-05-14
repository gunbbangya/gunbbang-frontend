"use client";
import React, { useState } from "react";
// 💡 CustomOverlayMap이 추가되었습니다! (마커를 내 마음대로 예쁘게 꾸미는 도구)
import { Map, CustomOverlayMap, useKakaoLoader } from "react-kakao-maps-sdk";
import { X, Navigation, Search } from "lucide-react";

type MapOverlayLabels = {
  loading: string;
  loadError: string;
  findFlags: string;
  searchPlaceholder: string;
  searchNoResults: string;
  geolocationError: string;
};

function pickFlagDisplayName(
  place: { name?: string; romanizedName?: string; translatedName?: string },
  preferRomanized: boolean
): string {
  const name = (place.name || "").trim();
  if (!preferRomanized) return name;
  const r = (place.romanizedName || "").trim();
  const t = (place.translatedName || "").trim();
  return r || t || name;
}

export default function MapOverlay({
  onClose,
  preferRomanizedLabels = false,
  labels,
}: {
  onClose: () => void;
  preferRomanizedLabels?: boolean;
  labels: MapOverlayLabels;
}) {
  const [loading, error] = useKakaoLoader({
    appkey: process.env.NEXT_PUBLIC_KAKAO_API_KEY || "", 
    libraries: ["services", "clusterer"],
  });

  const [map, setMap] = useState<any>(null);
  const [keyword, setKeyword] = useState(""); 
  
  // 💡 지도에 띄울 깃발 데이터를 담을 상태 (이름, 주소, 점수, 위도, 경도)
  const [markers, setMarkers] = useState<
    { displayName: string; address: string; score: number; lat: number; lng: number; isTrophy: boolean }[]
  >([]);

  const defaultCenter = { lat: 37.4979, lng: 127.0276 };

  // 📍 내 위치로 이동
  const handleMyLocation = () => {
    if (navigator.geolocation && map) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          const kakao = (window as any).kakao;
          const moveLatLon = new kakao.maps.LatLng(lat, lng);
          map.panTo(moveLatLon);
        },
        () => alert(labels.geolocationError)
      );
    }
  };

  // 🔍 장소/동네 검색 
  const searchLocation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim() || !map) return;

    const kakao = (window as any).kakao;
    const ps = new kakao.maps.services.Places();

    ps.keywordSearch(keyword, (data: any, status: any) => {
      if (status === kakao.maps.services.Status.OK) {
        const bounds = new kakao.maps.LatLngBounds();
        for (let i = 0; i < data.length; i++) {
          bounds.extend(new kakao.maps.LatLng(data[i].y, data[i].x));
        }
        map.setBounds(bounds);
      } else {
        alert(labels.searchNoResults);
      }
    });
  };

  // 🚩 이 근처 깃발 찾기 (완성판!)
  const handleFindFlags = async () => {
    try {
      // 1. 기존 마커 초기화
      setMarkers([]); 
      
      // 2. 백엔드에서 3.5점 이상 맛집 리스트 받아오기 (로컬 개발 시에는 http://localhost:10000 으로 바꿔야 할 수도 있습니다)
      const apiBase =
        process.env.NEXT_PUBLIC_BACKEND_URL ?? "https://gunbbang-backend.onrender.com";
      const res = await fetch(`${apiBase}/api/map-flags`);
      const data = await res.json();

      const kakao = (window as any).kakao;
      const geocoder = new kakao.maps.services.Geocoder();

      // 💡 에러 방지: 응답(data)이 배열인지 확인하고, 아니면 내부 배열(data.data 등)을 빼옵니다.
      const placesArray = Array.isArray(data) ? data : (data.places || data.data || []);

      // 3. 주소를 (위도, 경도) 좌표로 변환해서 지도에 뿌리기
      placesArray.forEach((place: any) => {
        // 💡 "대한민국", "KR", "번지" 같은 불필요한 글자를 지워야 카카오가 인식합니다.
        const cleanAddress = place.address.replace("대한민국", "").replace("KR", "").replace("번지", "").trim();
        const score = typeof place.score === "number" ? place.score : parseFloat(place.score) || 0;
        const isTrophy = typeof place.isTrophy === "boolean" ? place.isTrophy : score >= 4.0;

        geocoder.addressSearch(cleanAddress, (result: any, status: any) => {
          if (status === kakao.maps.services.Status.OK) {
            const displayName = pickFlagDisplayName(place, preferRomanizedLabels);
            setMarkers((prev) => [
              ...prev,
              {
                displayName,
                address: place.address,
                score,
                isTrophy,
                lat: parseFloat(result[0].y),
                lng: parseFloat(result[0].x),
              },
            ]);
          }
        });
      });
      
    } catch (error) {
      console.error("깃발 데이터를 불러오는 중 오류 발생:", error);
    }
  };

  return (
    <div className="fixed inset-0 z-[999] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="relative h-[85%] w-[90%] max-w-4xl overflow-hidden rounded-3xl bg-white shadow-2xl animate-in zoom-in-95 duration-300">
        
        <form onSubmit={searchLocation} className="absolute left-1/2 top-4 z-10 flex w-[90%] -translate-x-1/2 items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder={labels.searchPlaceholder}
              className="w-full rounded-full border-none bg-white/90 px-12 py-3.5 text-sm font-medium shadow-lg backdrop-blur-md outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <button type="button" onClick={onClose} className="flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-lg transition hover:bg-slate-100 shrink-0">
            <X className="h-6 w-6 text-slate-700" />
          </button>
        </form>

        {loading ? (
          <div className="flex h-full items-center justify-center bg-slate-100 text-slate-500 font-medium">{labels.loading}</div>
        ) : error ? (
          <div className="flex h-full items-center justify-center bg-slate-100 text-red-500 font-medium">{labels.loadError}</div>
        ) : (
          <Map center={defaultCenter} style={{ width: "100%", height: "100%" }} level={4} onCreate={setMap}>
            
            {/* 💡 백엔드에서 받아온 깃발(말풍선)들을 지도 위에 꽂아줍니다! */}
            {markers.map((marker, index) => (
              <CustomOverlayMap
                key={index}
                position={{ lat: marker.lat, lng: marker.lng }}
                yAnchor={1.2} // 마커 꼬리가 실제 위치를 정확히 가리키도록 위치 조정
              >
                <div className="flex flex-col items-center hover:scale-110 transition-transform cursor-pointer group">
                  {/* 말풍선 몸통 */}
                  <div className={`px-2.5 py-1.5 text-[11px] font-black text-white rounded-xl shadow-lg flex items-center gap-1 border border-white/20 
                    ${marker.isTrophy ? 'bg-gradient-to-r from-amber-400 to-yellow-500' : 'bg-slate-700'}
                  `}>
                    <span>{marker.isTrophy ? '🏆' : '🚩'}</span>
                    <span>{marker.score.toFixed(1)}</span>
                  </div>
                  {/* 말풍선 꼬리 */}
                  <div className={`w-2.5 h-2.5 rotate-45 -mt-1 shadow-sm 
                    ${marker.isTrophy ? 'bg-amber-500' : 'bg-slate-700'}
                  `}></div>
                  
                  {/* 마우스를 올리면 가게 이름이 스르륵 나타남! */}
                  <div className="absolute top-[-30px] opacity-0 group-hover:opacity-100 transition-opacity bg-white text-slate-800 text-[10px] font-bold px-2 py-1 rounded-md shadow-md whitespace-nowrap">
                    {marker.displayName}
                  </div>
                </div>
              </CustomOverlayMap>
            ))}

          </Map>
        )}

        <button onClick={handleMyLocation} className="absolute bottom-6 right-6 z-10 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-xl transition hover:bg-blue-700 hover:scale-105">
          <Navigation className="h-6 w-6 pr-0.5 pt-0.5" />
        </button>
        
        <button onClick={handleFindFlags} className="absolute bottom-6 left-1/2 z-10 -translate-x-1/2 rounded-full bg-slate-900 px-6 py-3.5 font-bold text-white shadow-xl transition hover:bg-slate-800 focus:scale-95">
          {labels.findFlags}
        </button>

      </div>
    </div>
  );
}