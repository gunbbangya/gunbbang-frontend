"use client";

import { useEffect, useState } from "react";
import { Loader2, Search } from "lucide-react";

const LOADING_MESSAGES = [
  "카카오맵 리뷰어들의 과거 이력을 추적 중입니다...",
  "알바성 리뷰 패턴을 필터링하고 있습니다...",
  "맛, 가성비, 친절 지표를 계산 중입니다...",
  "진짜 평점을 도출하고 있습니다...",
];

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [messageIndex, setMessageIndex] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [realScore, setRealScore] = useState<number | null>(null);
  const [aiSummary, setAiSummary] = useState<string>("");
  const [chartDetails, setChartDetails] = useState<{
    taste: number;
    value: number;
    service: number;
    time: number;
  } | null>(null);

  const [selectedPlace, setSelectedPlace] = useState<{
    place_name: string;
    address_name: string;
    place_url?: string; 
  } | null>(null);
  
  const [searchResults, setSearchResults] = useState<
    { place_name: string; address_name: string; place_url: string }[]
  >([]);

  useEffect(() => {
    if (!isAnalyzing) return;
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % LOADING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [isAnalyzing]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!searchQuery.trim()) return;
    setShowResult(false);
    setSelectedPlace(null);
    setSearchResults([]);
    setIsSearching(true);

    const fetchSearchResults = async () => {
      try {
        const params = new URLSearchParams({ q: searchQuery.trim() });
        const response = await fetch(
          `https://gunbbang-backend.onrender.com/api/search?${params.toString()}`
        );

        if (!response.ok) throw new Error("Search response not ok");

        const data: { place_name: string; address_name: string; place_url: string }[] = await response.json();
        setSearchResults(data);
      } catch (error) {
        console.error(error);
        alert("검색 중 오류가 발생했습니다.");
      } finally {
        setIsSearching(false);
      }
    };
    void fetchSearchResults();
  };

  const handleAnalyzePlace = (place: {
    place_name: string;
    address_name: string;
    place_url: string;
  }) => {
    setSelectedPlace(place);
    setIsAnalyzing(true);

    const fetchAnalysis = async () => {
      try {
        const query = place.place_url; 
        
        const response = await fetch("https://gunbbang-backend.onrender.com", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });

        if (!response.ok) throw new Error("Analyze response not ok");

        const data = await response.json();
        
        // 🚨 [여기에 CCTV 추가 완료!] F12(개발자 도구) 콘솔창에서 AI가 뭐라고 보냈는지 확인 가능합니다.
        console.log("🤖 AI가 보낸 원본 데이터:", data);

        // 🚨 [방어막 추가 완료!] 이름이 살짝 달라도 찰떡같이 알아듣게 처리합니다.
        setRealScore(data.realScore ?? data.score ?? 0);
        setAiSummary(data.aiSummary ?? "요약 데이터를 불러오지 못했습니다.");
        setChartDetails(data.details ?? { taste: 0, value: 0, service: 0, time: 0 });
        
        setIsAnalyzing(false);
        setShowResult(true);
      } catch (error) {
        console.error(error);
        alert("판독 불가: 리뷰 데이터가 충분하지 않거나 분석 중 오류가 발생했습니다."); 
        setIsAnalyzing(false);
        setShowResult(false);
      }
    };
    void fetchAnalysis();
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-xl">
        {showResult ? (
          <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="px-4 pt-8 sm:px-6 sm:pt-10">
              <div className="space-y-8">
                
                <header className="space-y-4">
                  <div>
                    <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700 border border-emerald-100 mb-4">
                      분석 완료
                    </span>
                    
                    {/* 🚨 화면 터짐 방지용 철벽 방어막 작동 중 */}
                    {typeof realScore === 'number' && (
                      <div className="flex flex-col gap-2">
                        {realScore >= 4.0 && (
                          <div className="self-start mb-1 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-red-500 to-orange-500 px-3 py-1.5 text-sm font-extrabold text-white shadow-md animate-pulse">
                            <span>🏆</span> 전국구 인생 맛집 인정!
                          </div>
                        )}
                        
                        <div>
                          <p className="text-xs font-semibold text-slate-500 mb-1">AI 찐-뷰 평점</p>
                          <p className="text-5xl font-extrabold tracking-tight text-slate-800">
                            {realScore.toFixed(1)}{" "}
                            <span className="text-xl font-medium text-slate-300">/ 5.0</span>
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600 space-y-1.5 mt-4">
                    <p>👑 <strong className="text-slate-800">4.0 이상</strong> : 전국구 인생 맛집 (매우 드묾)</p>
                    <p>👍 <strong className="text-slate-800">3.0 이상</strong> : 정말 훌륭한 찐 맛집</p>
                    <p>🙂 <strong className="text-slate-800">2.5 이상</strong> : 실패 없는 괜찮은 식당</p>
                  </div>
                </header>

                <section className="space-y-6">
                  <div className="rounded-2xl border border-blue-100 bg-blue-50/50 px-4 py-4 text-sm text-slate-700">
                    <p className="mb-2 text-xs font-bold text-blue-600 flex items-center gap-1">
                      <span>🤖</span> AI 팩트 체크 요약
                    </p>
                    <p className="leading-relaxed">
                      {aiSummary}
                    </p>
                  </div>

                  {chartDetails && (
                    <div>
                      <h3 className="text-sm font-bold text-slate-800 mb-3">📊 부문별 상세 분석</h3>
                      <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                        
                        <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">😋 맛</span>
                          <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-orange-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.taste / 5) * 100}%` }}></div>
                          </div>
                          <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.taste}/5</span>
                        </div>

                        <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">💰 가성비</span>
                          <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-green-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.value / 5) * 100}%` }}></div>
                          </div>
                          <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.value}/5</span>
                        </div>

                        <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">🧹 서비스</span>
                          <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.service / 5) * 100}%` }}></div>
                          </div>
                          <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.service}/5</span>
                        </div>

                        <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">⏳ 대기/속도</span>
                          <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-purple-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.time / 5) * 100}%` }}></div>
                          </div>
                          <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.time}/5</span>
                        </div>

                      </div>
                    </div>
                  )}
                </section>

                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery("");
                    setShowResult(false);
                  }}
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 shadow-sm"
                >
                  다른 맛집 검색하기
                </button>
              </div>
            </div>

            <div className="mt-8 bg-slate-50 px-6 py-4 border-t border-slate-200">
              <p className="text-[10px] text-slate-400 leading-relaxed break-keep">
                * 본 지표는 공개된 사용자 리뷰를 AI가 요약·분석한 추정치로, 실제 매장의 품질과 100% 일치하지 않을 수 있으며 법적 증빙 자료로 활용될 수 없습니다.
              </p>
            </div>
          </section>
        ) : !isAnalyzing ? (
          <>
            <header className="mb-8 text-center">
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                진짜 맛집을 찾으세요?
              </h1>
              <p className="mt-3 text-sm sm:text-base text-slate-500">
                광고와 가짜 리뷰를 걸러낸 진짜 평점을 확인하세요.
              </p>
            </header>

            <section className="rounded-2xl border border-slate-200 bg-white px-4 py-5 shadow-sm sm:px-6 sm:py-6 space-y-4">
              <form className="flex flex-col gap-3 sm:flex-row sm:items-center" onSubmit={handleSubmit}>
                <label className="flex-1">
                  <span className="mb-2 block text-xs font-medium text-slate-600">검색</span>
                  <div className="relative">
                    <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400">
                      <Search className="h-4 w-4" />
                    </span>
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(event) => setSearchQuery(event.target.value)}
                      placeholder="식당 이름이나 카카오맵 링크를 입력하세요..."
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-10 py-3 text-sm sm:text-base text-slate-900 placeholder:text-slate-400 outline-none ring-0 transition focus:border-slate-400 focus:bg-white focus:shadow-[0_0_0_1px_rgba(148,163,184,0.75)]"
                    />
                  </div>
                </label>
                <button
                  type="submit"
                  disabled={!searchQuery.trim() || isSearching}
                  className="mt-1 inline-flex items-center justify-center rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 sm:mt-7 sm:min-w-[120px]"
                >
                  {isSearching ? "검색 중..." : "검색"}
                </button>
              </form>

              <p className="text-[11px] text-center text-slate-400 animate-in fade-in duration-700">
                ℹ️ 최근 7일 내 분석 기록이 있는 가게는 결과가 즉시 제공됩니다.
              </p>

              {searchResults.length > 0 && (
                <div className="border-t border-slate-100 pt-4">
                  <p className="mb-2 text-xs font-medium text-slate-500">검색 결과</p>
                  <div className="max-h-64 overflow-y-auto pr-1">
                    <ul className="space-y-2">
                      {searchResults.map((place) => (
                        <li key={`${place.place_name}-${place.address_name}`}>
                          <button
                            type="button"
                            onClick={() => handleAnalyzePlace(place)}
                            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-800 transition hover:bg-slate-100 hover:border-slate-300"
                          >
                            <p className="font-medium text-slate-900">{place.place_name}</p>
                            <p className="mt-0.5 text-xs text-slate-500">{place.address_name}</p>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </section>
          </>
        ) : (
          <section className="rounded-2xl border border-slate-200 bg-white px-4 py-8 shadow-sm sm:px-6 sm:py-10">
            <div className="flex flex-col items-center text-center gap-6">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 text-slate-600 animate-spin" />
                <p className="text-sm font-medium text-slate-800">분석을 진행하고 있습니다</p>
                <p className="text-sm text-slate-500 min-h-[1.5rem]">{LOADING_MESSAGES[messageIndex]}</p>
              </div>
              <div className="w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-16 text-sm text-slate-400 sm:py-20 flex items-center justify-center">
                <span>[ AI 판독 엔진 가동 중 ]</span>
              </div>
              <button
                type="button"
                onClick={() => setIsAnalyzing(false)}
                className="text-xs text-slate-500 underline-offset-2 hover:underline"
              >
                분석 취소
              </button>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}