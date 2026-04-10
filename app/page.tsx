  "use client";
  //hello
  import { useEffect, useState } from "react";
  import { Loader2, Search } from "lucide-react";

type Lang = "ko" | "en";

const LANG_STORAGE_KEY = "jjin-view:lang";

const translations: Record<
  Lang,
  {
    loadingMessages: string[];
    statusDone: string;
    heroTitle: string;
    heroSubtitle: string;
    searchLabel: string;
    searchPlaceholder: string;
    searchButton: string;
    searching: string;
    recentHint: string;
    searchResultsTitle: string;
    analyzingTitle: string;
    analyzingEngineLabel: string;
    cancelAnalyze: string;
    scoreTitle: string;
    scoreOutOf: string;
    trophyText: string;
    legend4: string;
    legend3: string;
    legend25: string;
    aiSummaryTitle: string;
    detailsTitle: string;
    categoryTaste: string;
    categoryValue: string;
    categoryService: string;
    categoryTime: string;
    searchAgain: string;
    disclaimer: string;
    searchError: string;
    analyzeError: string;
    missingSummaryFallback: string;
  }
> = {
  ko: {
    loadingMessages: [
      "구글 리뷰 분석기의 과거 이력을 추적 중입니다...",
      "광고성 리뷰 패턴을 필터링하고 있습니다...",
      "맛, 가성비, 서비스 지표를 계산 중입니다...",
      "진짜 평점을 도출하고 있습니다...",
    ],
    statusDone: "분석 완료",
    heroTitle: "진짜 맛집을 찾으세요?",
    heroSubtitle: "광고와 가짜 리뷰를 걸러낸 진짜 평점을 확인하세요.",
    searchLabel: "검색",
    searchPlaceholder: "식당 이름이나 구글/지도 링크를 입력하세요...",
    searchButton: "검색",
    searching: "검색 중...",
    recentHint: "ℹ️ 최근 7일 내 분석 기록이 있는 가게는 결과가 즉시 제공됩니다.",
    searchResultsTitle: "검색 결과",
    analyzingTitle: "분석을 진행하고 있습니다",
    analyzingEngineLabel: "[ AI 판독 엔진 가동 중 ]",
    cancelAnalyze: "분석 취소",
    scoreTitle: "AI 찐-뷰 평점",
    scoreOutOf: "/ 5.0",
    trophyText: "전국구 인생 맛집 인정!",
    legend4: "전국구 인생 맛집 (매우 드묾)",
    legend3: "정말 훌륭한 찐 맛집",
    legend25: "실패 없는 괜찮은 식당",
    aiSummaryTitle: "AI 팩트 체크 요약",
    detailsTitle: "📊 부문별 상세 분석",
    categoryTaste: "😋 맛",
    categoryValue: "💰 가성비",
    categoryService: "🧹 서비스",
    categoryTime: "⏳ 대기/속도",
    searchAgain: "다른 맛집 검색하기",
    disclaimer:
      "* 본 지표는 공개된 사용자 리뷰를 AI가 요약·분석한 추정치로, 실제 매장의 품질과 100% 일치하지 않을 수 있으며 법적 증빙 자료로 활용될 수 없습니다.",
    searchError: "검색 중 오류가 발생했습니다.",
    analyzeError:
      "판독 불가: 리뷰 데이터가 충분하지 않거나 분석 중 오류가 발생했습니다.",
    missingSummaryFallback: "요약 데이터를 불러오지 못했습니다.",
  },
  en: {
    loadingMessages: [
      "Tracking reviewer history with a Google Review Analyzer...",
      "Filtering out suspicious/promotional review patterns...",
      "Calculating taste, value, and service signals...",
      "Deriving a more reliable score...",
    ],
    statusDone: "Analysis complete",
    heroTitle: "Looking for a truly great place to eat?",
    heroSubtitle: "See a score that filters out ads and fake reviews.",
    searchLabel: "Search",
    searchPlaceholder: "Enter a restaurant name or a Google/Maps link...",
    searchButton: "Search",
    searching: "Searching...",
    recentHint: "ℹ️ Places analyzed in the last 7 days may return instantly.",
    searchResultsTitle: "Results",
    analyzingTitle: "Analyzing...",
    analyzingEngineLabel: "[ AI engine running ]",
    cancelAnalyze: "Cancel",
    scoreTitle: "AI Real-View score",
    scoreOutOf: "/ 5.0",
    trophyText: "National-tier, life-changing spot!",
    legend4: "National-tier gem (rare)",
    legend3: "Truly great, reliable pick",
    legend25: "Solid choice, low risk",
    aiSummaryTitle: "AI Fact Checker Summary",
    detailsTitle: "📊 Category breakdown",
    categoryTaste: "😋 Taste",
    categoryValue: "💰 Value",
    categoryService: "🧹 Service",
    categoryTime: "⏳ Wait/Speed",
    searchAgain: "Search another place",
    disclaimer:
      "* This score is an AI-estimated summary/analysis of publicly available reviews and may not fully match the actual quality. It should not be used as legal evidence.",
    searchError: "An error occurred while searching.",
    analyzeError:
      "Unable to analyze: not enough review data or an error occurred during analysis.",
    missingSummaryFallback: "Failed to load the summary.",
  },
};

export default function HomePage() {
  const [lang, setLang] = useState<Lang>("ko");
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
      name: string;
      address: string;
    } | null>(null);
    
    const [searchResults, setSearchResults] = useState<
      { name: string; address: string; }[]
    >([]);

  const setLanguage = (nextLang: Lang) => {
    setLang(nextLang);
    try {
      localStorage.setItem(LANG_STORAGE_KEY, nextLang);
    } catch {
      // ignore storage errors (private mode, blocked storage, etc.)
    }
  };

  useEffect(() => {
    try {
      const stored = localStorage.getItem(LANG_STORAGE_KEY);
      if (stored === "ko" || stored === "en") setLang(stored);
    } catch {
      // ignore storage errors (private mode, blocked storage, etc.)
    }
  }, []);

    useEffect(() => {
      if (!isAnalyzing) return;
    const loadingMessages = translations[lang].loadingMessages;
      const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % loadingMessages.length);
      }, 2500);
      return () => clearInterval(interval);
  }, [isAnalyzing, lang]);

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

          const data: { name: string; address: string; }[] = await response.json();
          setSearchResults(data);
        } catch (error) {
          console.error(error);
        alert(translations[lang].searchError);
        } finally {
          setIsSearching(false);
        }
      };
      void fetchSearchResults();
    };

    const handleAnalyzePlace = (place: {
      name: string;
      address: string;
    }) => {
      setSelectedPlace(place);
      setIsAnalyzing(true);

      const fetchAnalysis = async () => {
        try {
          // 💡 1. 쿼리에는 무조건 '식당 이름'이 들어가야 합니다!
          const query = place.name;
          
          const response = await fetch("https://gunbbang-backend.onrender.com/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // 💡 2. 바디에 query와 lang이 둘 다 예쁘게 포장되어야 합니다!
          body: JSON.stringify({ query: query, lang }),
          });

          if (!response.ok) throw new Error("Analyze response not ok");

          const data = await response.json();
          
          // 🚨 [여기에 CCTV 추가 완료!]
          console.log("🤖 AI가 보낸 원본 데이터:", data);

          // 🚨 [방어막 추가 완료!]
          setRealScore(data.realScore ?? data.score ?? 0);
        setAiSummary(data.aiSummary ?? translations[lang].missingSummaryFallback);
          setChartDetails(data.details ?? { taste: 0, value: 0, service: 0, time: 0 });
          
          setIsAnalyzing(false);
          setShowResult(true);
        } catch (error) {
          console.error(error);
        alert(translations[lang].analyzeError); 
          setIsAnalyzing(false);
          setShowResult(false);
        }
      };
      void fetchAnalysis();
    };

    return (
      <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-xl">
        <div className="mb-4 flex justify-end">
          <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
            <button
              type="button"
              onClick={() => setLanguage("ko")}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                lang === "ko"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
              aria-pressed={lang === "ko"}
            >
              KR
            </button>
            <button
              type="button"
              onClick={() => setLanguage("en")}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                lang === "en"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
              aria-pressed={lang === "en"}
            >
              EN
            </button>
          </div>
        </div>
          {showResult ? (
            <section className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="px-4 pt-8 sm:px-6 sm:pt-10">
                <div className="space-y-8">
                  
                  <header className="space-y-4">
                    <div>
                      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700 border border-emerald-100 mb-4">
                      {translations[lang].statusDone}
                      </span>
                      
                      {/* 🚨 화면 터짐 방지용 철벽 방어막 작동 중 */}
                      {typeof realScore === 'number' && (
                        <div className="flex flex-col gap-2">
                          {realScore >= 4.0 && (
                            <div className="self-start mb-1 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-red-500 to-orange-500 px-3 py-1.5 text-sm font-extrabold text-white shadow-md animate-pulse">
                            <span>🏆</span> {translations[lang].trophyText}
                            </div>
                          )}
                          
                          <div>
                          <p className="text-xs font-semibold text-slate-500 mb-1">{translations[lang].scoreTitle}</p>
                            <p className="text-5xl font-extrabold tracking-tight text-slate-800">
                              {realScore.toFixed(1)}{" "}
                            <span className="text-xl font-medium text-slate-300">{translations[lang].scoreOutOf}</span>
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="rounded-xl border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600 space-y-1.5 mt-4">
                    <p>👑 <strong className="text-slate-800">4.0+</strong> : {translations[lang].legend4}</p>
                    <p>👍 <strong className="text-slate-800">3.0+</strong> : {translations[lang].legend3}</p>
                    <p>🙂 <strong className="text-slate-800">2.5+</strong> : {translations[lang].legend25}</p>
                    </div>
                  </header>

                  <section className="space-y-6">
                    <div className="rounded-2xl border border-blue-100 bg-blue-50/50 px-4 py-4 text-sm text-slate-700">
                      <p className="mb-2 text-xs font-bold text-blue-600 flex items-center gap-1">
                      <span>🤖</span> {translations[lang].aiSummaryTitle}
                      </p>
                      <p className="leading-relaxed">
                        {aiSummary}
                      </p>
                    </div>

                    {chartDetails && (
                      <div>
                      <h3 className="text-sm font-bold text-slate-800 mb-3">{translations[lang].detailsTitle}</h3>
                        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                          
                          <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">{translations[lang].categoryTaste}</span>
                            <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                              <div className="h-full bg-orange-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.taste / 5) * 100}%` }}></div>
                            </div>
                            <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.taste}/5</span>
                          </div>

                          <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">{translations[lang].categoryValue}</span>
                            <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                              <div className="h-full bg-green-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.value / 5) * 100}%` }}></div>
                            </div>
                            <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.value}/5</span>
                          </div>

                          <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">{translations[lang].categoryService}</span>
                            <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                              <div className="h-full bg-blue-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.service / 5) * 100}%` }}></div>
                            </div>
                            <span className="w-10 text-right text-slate-500 font-semibold">{chartDetails.service}/5</span>
                          </div>

                          <div className="flex items-center text-sm">
                          <span className="w-20 font-medium text-slate-600">{translations[lang].categoryTime}</span>
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
                  {translations[lang].searchAgain}
                  </button>
                </div>
              </div>

              <div className="mt-8 bg-slate-50 px-6 py-4 border-t border-slate-200">
                <p className="text-[10px] text-slate-400 leading-relaxed break-keep">
                {translations[lang].disclaimer}
                </p>
              </div>
            </section>
          ) : !isAnalyzing ? (
            <>
              <header className="mb-8 text-center">
                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                {translations[lang].heroTitle}
                </h1>
                <p className="mt-3 text-sm sm:text-base text-slate-500">
                {translations[lang].heroSubtitle}
                </p>
              </header>

              <section className="rounded-2xl border border-slate-200 bg-white px-4 py-5 shadow-sm sm:px-6 sm:py-6 space-y-4">
                <form className="flex flex-col gap-3 sm:flex-row sm:items-center" onSubmit={handleSubmit}>
                  <label className="flex-1">
                  <span className="mb-2 block text-xs font-medium text-slate-600">{translations[lang].searchLabel}</span>
                    <div className="relative">
                      <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-400">
                        <Search className="h-4 w-4" />
                      </span>
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(event) => setSearchQuery(event.target.value)}
                      placeholder={translations[lang].searchPlaceholder}
                        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-10 py-3 text-sm sm:text-base text-slate-900 placeholder:text-slate-400 outline-none ring-0 transition focus:border-slate-400 focus:bg-white focus:shadow-[0_0_0_1px_rgba(148,163,184,0.75)]"
                      />
                    </div>
                  </label>
                  <button
                    type="submit"
                    disabled={!searchQuery.trim() || isSearching}
                    className="mt-1 inline-flex items-center justify-center rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 sm:mt-7 sm:min-w-[120px]"
                  >
                  {isSearching ? translations[lang].searching : translations[lang].searchButton}
                  </button>
                </form>

                <p className="text-[11px] text-center text-slate-400 animate-in fade-in duration-700">
                {translations[lang].recentHint}
                </p>

                {searchResults.length > 0 && (
                  <div className="border-t border-slate-100 pt-4">
                  <p className="mb-2 text-xs font-medium text-slate-500">{translations[lang].searchResultsTitle}</p>
                    <div className="max-h-64 overflow-y-auto pr-1">
                      <ul className="space-y-2">
                        {searchResults.map((place) => (
                          <li key={`${place.name}-${place.address}`}>
                            <button
                              type="button"
                              onClick={() => handleAnalyzePlace(place)}
                              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-800 transition hover:bg-slate-100 hover:border-slate-300"
                            >
                              <p className="font-medium text-slate-900">{place.name}</p>
                              <p className="mt-0.5 text-xs text-slate-500">{place.address}</p>
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
                <p className="text-sm font-medium text-slate-800">{translations[lang].analyzingTitle}</p>
                <p className="text-sm text-slate-500 min-h-[1.5rem]">{translations[lang].loadingMessages[messageIndex]}</p>
                </div>
                <div className="w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-16 text-sm text-slate-400 sm:py-20 flex items-center justify-center">
                <span>{translations[lang].analyzingEngineLabel}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAnalyzing(false)}
                  className="text-xs text-slate-500 underline-offset-2 hover:underline"
                >
                {translations[lang].cancelAnalyze}
                </button>
              </div>
            </section>
          )}
        </div>
      </main>
    );
  }