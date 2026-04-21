"use client";
import { useEffect, useState } from "react";
import { Loader2, Search, Map } from "lucide-react";
import MapOverlay from "./MapOverlay"; 
import confetti from "canvas-confetti";

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
    fakeReviewTitle: string;
    fakeReviewDesc: string;
    limitExceeded: string;
    overloadError: string;
    energyLabel: string;
    // 💡 새로 추가된 번역 (고급 검색 관련)
    advancedButton: string;
    returnBasic: string;
    advancedStatus: string;
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
    analyzeError: "판독 불가: 리뷰 데이터가 충분하지 않거나 분석 중 오류가 발생했습니다.",
    missingSummaryFallback: "요약 데이터를 불러오지 못했습니다.",
    fakeReviewTitle: "리뷰 조작 정황 포착",
    fakeReviewDesc: "음식에 대한 구체적 평가보다 보상형/친절 묘사가 비정상적으로 많습니다. 평점의 거품을 걷어냈습니다.",
    limitExceeded: "오늘 할당된 15회의 분석 에너지를 모두 소모했습니다. 내일 다시 찾아주세요!",
    overloadError: "현재 접속자가 많아 AI가 과부하 상태입니다. 약 1분 후 다시 시도해 주세요!",
    energyLabel: "오늘의 분석 에너지",
    advancedButton: "🔥 고급 심층 분석 보기",
    returnBasic: "↩️ 구글 기본 요약으로 돌아가기",
    advancedStatus: "🔥 심층 분석 완료",
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
    analyzeError: "Unable to analyze: not enough review data or an error occurred during analysis.",
    missingSummaryFallback: "Failed to load the summary.",
    fakeReviewTitle: "Fake Review Pattern Detected",
    fakeReviewDesc: "Abnormally high ratio of reward-based or non-food related praise detected. Score adjusted accordingly.",
    limitExceeded: "You have used all 15 analysis energies for today. Please come back tomorrow!",
    overloadError: "AI is currently overloaded. Please try again in about 1 minute!",
    energyLabel: "Daily Energy",
    advancedButton: "🔥 View Advanced Deep Analysis",
    returnBasic: "↩️ Return to Basic Google Summary",
    advancedStatus: "🔥 Deep Analysis Complete",
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
  const [eventProb, setEventProb] = useState<number>(0);
  const [aiSummary, setAiSummary] = useState<string>("");
  const [chartDetails, setChartDetails] = useState<{
    taste: number;
    value: number;
    service: number;
    time: number;
  } | null>(null);

  // 💡 고급 검색용 상태들 추가!
  const [hasAdvanced, setHasAdvanced] = useState(false);
  const [kakaoData, setKakaoData] = useState<any>(null);
  const [basicData, setBasicData] = useState<any>(null);
  const [isAdvancedView, setIsAdvancedView] = useState(false);

  const [selectedPlace, setSelectedPlace] = useState<{
    name: string;
    address: string;
  } | null>(null);

  const [searchResults, setSearchResults] = useState<{ name: string; address: string }[]>([]);

  const [isMapOpen, setIsMapOpen] = useState(false);
  const [redFlags, setRedFlags] = useState(0);
  const [goldFlags, setGoldFlags] = useState(0);
  const [userDailyCount, setUserDailyCount] = useState(0);

  const isCritical = showResult && realScore !== null && realScore <= 2.4;

  const googleScore = basicData?.score ?? 0;
  const kakaoScore = kakaoData?.realScore ?? 0;
  const scoreDiff = parseFloat((googleScore - kakaoScore).toFixed(1));


  const setLanguage = (nextLang: Lang) => {
    setLang(nextLang);
    try {
      localStorage.setItem(LANG_STORAGE_KEY, nextLang);
    } catch { }
  };

  useEffect(() => {
    try {
      const stored = localStorage.getItem(LANG_STORAGE_KEY);
      if (stored === "ko" || stored === "en") setLang(stored);
    } catch { }
  }, []);

  useEffect(() => {
    try {
      const storedRed = localStorage.getItem("jjin-view:redFlags");
      const storedGold = localStorage.getItem("jjin-view:goldFlags");
      if (storedRed) setRedFlags(parseInt(storedRed, 10));
      if (storedGold) setGoldFlags(parseInt(storedGold, 10));

      const savedData = JSON.parse(localStorage.getItem('zzinview_usage') || '{}');
      const today = new Date().toLocaleDateString();

      if (savedData.date === today) {
        setUserDailyCount(savedData.count || 0);
      } else {
        localStorage.setItem('zzinview_usage', JSON.stringify({ date: today, count: 0 }));
        setUserDailyCount(0);
      }
    } catch { }
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
    
    // 💡 검색 새로 할 때 고급 뷰 상태 초기화
    setHasAdvanced(false);
    setKakaoData(null);
    setBasicData(null);
    setIsAdvancedView(false);

    const fetchSearchResults = async () => {
      try {
        const params = new URLSearchParams({ q: searchQuery.trim() });
        const response = await fetch(
          `https://gunbbang-backend.onrender.com/api/search?${params.toString()}`
        );
        if (!response.ok) throw new Error("Search response not ok");

        const data: { name: string; address: string }[] = await response.json();
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

  const handleAnalyzePlace = (place: { name: string; address: string }) => {
    if (userDailyCount >= 1500) {
      alert(translations[lang].limitExceeded);
      return;
    }

    setSelectedPlace(place);
    setIsAnalyzing(true);

    const fetchAnalysis = async () => {
      try {
        const query = place.name;
        const response = await fetch("https://gunbbang-backend.onrender.com/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query, address: place.address, lang }),
        });

        if (response.status === 429) {
          alert(translations[lang].overloadError);
          setIsAnalyzing(false);
          setShowResult(false);
          return;
        }

        if (!response.ok) throw new Error("Analyze response not ok");

        const newCount = userDailyCount + 1;
        setUserDailyCount(newCount);
        const today = new Date().toLocaleDateString();
        localStorage.setItem('zzinview_usage', JSON.stringify({ date: today, count: newCount }));

        const data = await response.json();
        console.log("🤖 AI가 보낸 원본 데이터:", data);

        const score = data.realScore ?? data.score ?? 0;
        const eProb = data.eventProbability ?? 0;
        const summary = data.aiSummary ?? translations[lang].missingSummaryFallback;
        const details = data.details ?? { taste: 0, value: 0, service: 0, time: 0 };

        // 💡 1. 기본 데이터 세팅 & 백업
        setRealScore(score);
        setEventProb(eProb);
        setAiSummary(summary);
        setChartDetails(details);
        setBasicData({ score, eProb, summary, details });

        // 💡 2. 고급 데이터가 있으면 세팅해두기 (버튼 띄울 준비)
        if (data.has_advanced && data.kakao_data) {
          setHasAdvanced(true);
          setKakaoData(data.kakao_data);
        } else {
          setHasAdvanced(false);
          setKakaoData(null);
        }

        if (score >= 3.5) {
          try {
            const flagRes = await fetch("https://gunbbang-backend.onrender.com/api/map-flags", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                name: place.name,
                address: place.address,
                score: score,
                aiSummary: data.aiSummary,
                details: data.details,
              }),
            });
            if (!flagRes.ok) throw new Error("DB 저장 실패");
          } catch (err) {
            console.error("❌ 깃발 저장 실패:", err);
          }
        }

        if (data.isNewDiscovery) {
          if (score >= 4.0) {
            confetti({ particleCount: 200, spread: 120, origin: { y: 0.6 }, colors: ['#FFD700', '#FFA500', '#FF8C00'] });
            setGoldFlags((prev) => {
              const next = prev + 1;
              localStorage.setItem("jjin-view:goldFlags", next.toString());
              return next;
            });
            alert(`🎉 [최초 발견] 대박! 4.0점 이상 황금 깃발 맛집을 발견하셨습니다!`);
          } else if (score >= 3.5) {
            confetti({ particleCount: 100, spread: 80, origin: { y: 0.6 }, colors: ['#FF0000', '#FFFFFF', '#FFB6C1'] });
            setRedFlags((prev) => {
              const next = prev + 1;
              localStorage.setItem("jjin-view:redFlags", next.toString());
              return next;
            });
            alert(`🚩 [최초 발견] 3.5점 이상! 빨간 깃발을 지도에 꽂았습니다!`);
          }
        }

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

  const remainingEnergy = Math.max(0, 15 - userDailyCount);
  const energyColorClass = remainingEnergy <= 3 
    ? "bg-orange-50 border-orange-200 text-orange-600" 
    : "bg-blue-50 border-blue-200 text-blue-700";

  return (
    <>
      {isMapOpen && <MapOverlay onClose={() => setIsMapOpen(false)} />}

      <main className={`min-h-screen flex items-center justify-center px-4 py-10 transition-colors duration-1000 ${isCritical ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
        <div className="w-full max-w-xl">
          
          <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
            <div className="flex gap-2">
              <div className="flex gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2 shadow-sm">
                <span className="text-sm font-bold text-slate-700">🚩 {redFlags}</span>
                <span className="text-sm font-bold text-slate-700">🏆 {goldFlags}</span>
              </div>
              
              <div className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 shadow-sm transition-colors ${energyColorClass}`}>
                <span className="text-sm font-bold">⚡ {translations[lang].energyLabel}: {remainingEnergy} / 15</span>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setIsMapOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-blue-600"
              >
                <Map className="h-4 w-4" />
                지도 보기
              </button>

              <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
                <button
                  type="button"
                  onClick={() => setLanguage("ko")}
                  className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${lang === "ko" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50"}`}
                >
                  KR
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage("en")}
                  className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${lang === "en" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50"}`}
                >
                  EN
                </button>
              </div>
            </div>
          </div>

          {showResult ? (
            <section className={`rounded-2xl border shadow-lg overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500 transition-colors ${isCritical ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
              {isCritical && (
                <div className="bg-red-900/80 py-1.5 text-center text-[10px] font-black tracking-[0.2em] text-red-100 uppercase animate-pulse">
                  Critical Low Score : Unreliable Place
                </div>
              )}

              <div className="px-4 pt-8 sm:px-6 sm:pt-10">
                <div className="space-y-8">
                 <header className="space-y-4">
                    <div>
                      {/* 💡 뱃지 텍스트 변경: 기본 뷰 vs 고급 뷰 */}
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium border mb-4 ${
                        isAdvancedView 
                          ? 'bg-amber-100 text-amber-800 border-amber-300' 
                          : isCritical ? 'bg-emerald-900/30 text-emerald-400 border-emerald-800' : 'bg-emerald-50 text-emerald-700 border-emerald-100'
                      }`}>
                        {isAdvancedView ? translations[lang].advancedStatus : translations[lang].statusDone}
                      </span>

                      {/* 💡 1. 구글 패턴 분석 기반 가짜 리뷰 경고 (기존 로직) */}
                      {eventProb >= 70 && (
                        <div className="mb-6 rounded-xl border-2 border-dashed border-red-500/60 bg-red-950/40 p-4 animate-in zoom-in duration-500">
                          <div className="flex items-start sm:items-center gap-3">
                            <span className="text-3xl animate-bounce mt-1 sm:mt-0">🚨</span>
                            <div>
                             <p className="text-sm font-bold text-red-400">
                              {translations[lang].fakeReviewTitle} ({eventProb}%)
                             </p>
                             <p className="text-xs text-red-100/90 mt-0.5 leading-relaxed break-keep">
                              {translations[lang].fakeReviewDesc}
                            </p>
                            </div>
                          </div>
                       </div>
                      )}
                    
{/* 💡 [새로 추가] 기본 검색 화면에서 보여주는 '고급 검색 점수 차이' 배너 */}
{!isAdvancedView && kakaoData && (
                        <>
                          {/* 거품 감지 (구글이 1.0점 이상 높음 -> 빨간색) */}
                          {scoreDiff >= 1.0 && (
                            <div className="mb-6 rounded-xl border-2 border-red-400 bg-red-50 px-4 py-3 text-red-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xl">🚨</span>
                                <p className="text-sm font-bold">
                                  {lang === "ko" ? `고급 분석 결과와 ${scoreDiff.toFixed(1)}점 차이납니다.` : `${scoreDiff.toFixed(1)} points diff from advanced analysis.`}
                                </p>
                              </div>
                            </div>
                          )}

                          {/* 거품 의심 (구글이 0.6 ~ 0.9점 높음 -> 노란색) */}
                          {scoreDiff >= 0.6 && scoreDiff < 1.0 && (
                            <div className="mb-6 rounded-xl border-2 border-amber-400 bg-amber-50 px-4 py-3 text-amber-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xl">⚠️</span>
                                <p className="text-sm font-bold">
                                  {lang === "ko" ? `고급 분석 결과와 ${scoreDiff.toFixed(1)}점 차이납니다.` : `${scoreDiff.toFixed(1)} points diff from advanced analysis.`}
                                </p>
                              </div>
                            </div>
                          )}

                          {/* 숨은 찐맛집 (카카오 점수가 오히려 더 높음 -> 파란색) */}
                          {scoreDiff < 0 && (
                            <div className="mb-6 rounded-xl border-2 border-blue-400 bg-blue-50 px-4 py-3 text-blue-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-start sm:items-center gap-2.5">
                                <span className="text-xl mt-0.5 sm:mt-0">💎</span>
                                <div>
                                  <p className="text-sm font-bold">
                                    {lang === "ko" ? "훌륭한 식당일 가능성이 있습니다." : "Highly likely to be an excellent restaurant."}
                                  </p>
                                  <p className="text-xs mt-0.5 opacity-90">
                                    {lang === "ko" ? "리뷰 조작 정황도가 있을 수 있으나, 실사용자 평점이 오히려 더 높습니다. 고급 검색을 참고해주세요." : "Despite possible review events, real user scores are even higher. Please check the deep analysis."}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    <div className={`rounded-xl border p-3 text-xs space-y-1.5 mt-4 ${isCritical ? 'bg-slate-800/50 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-100 text-slate-600'}`}>
                      <p>👑 <strong className={isCritical ? 'text-slate-200' : 'text-slate-800'}>4.0+</strong> : {translations[lang].legend4}</p>
                      <p>👍 <strong className={isCritical ? 'text-slate-200' : 'text-slate-800'}>3.0+</strong> : {translations[lang].legend3}</p>
                      <p>🙂 <strong className={isCritical ? 'text-slate-200' : 'text-slate-800'}>2.5+</strong> : {translations[lang].legend25}</p>
                    </div>
                  </header>

                  <section className="space-y-6">
                    <div className={`rounded-2xl border px-4 py-4 text-sm ${isCritical ? 'bg-blue-950/30 border-blue-900/50 text-slate-300' : 'bg-blue-50/50 border-blue-100 text-slate-700'}`}>
                      <p className={`mb-2 text-xs font-bold flex items-center gap-1 ${isCritical ? 'text-blue-400' : 'text-blue-600'}`}>
                        <span>{isAdvancedView ? "🔥" : "🤖"}</span> 
                        {isAdvancedView ? "카카오 심층 팩트 체크" : translations[lang].aiSummaryTitle}
                      </p>
                      {/* 💡 whitespace-pre-wrap 추가: 엔터(줄바꿈) 예쁘게 렌더링되게! */}
                      <p className="leading-relaxed whitespace-pre-wrap transition-all duration-500">
                        {aiSummary}
                      </p>
                    </div>

                    {chartDetails && (
                      <div>
                        <h3 className={`text-sm font-bold mb-3 ${isCritical ? 'text-slate-200' : 'text-slate-800'}`}>
                          {translations[lang].detailsTitle}
                        </h3>
                        <div className={`space-y-3 rounded-2xl border p-5 shadow-sm ${isCritical ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200'}`}>
                          
                          <div className="flex items-center text-sm">
                            <span className={`w-20 font-medium ${isCritical ? 'text-slate-400' : 'text-slate-600'}`}>{translations[lang].categoryTaste}</span>
                            <div className={`flex-1 h-2.5 rounded-full overflow-hidden ${isCritical ? 'bg-slate-700' : 'bg-slate-100'}`}>
                              <div className="h-full bg-orange-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.taste / 5) * 100}%` }}></div>
                            </div>
                            <span className={`w-10 text-right font-semibold ${isCritical ? 'text-slate-300' : 'text-slate-500'}`}>{chartDetails.taste}/5</span>
                          </div>

                          <div className="flex items-center text-sm">
                            <span className={`w-20 font-medium ${isCritical ? 'text-slate-400' : 'text-slate-600'}`}>{translations[lang].categoryValue}</span>
                            <div className={`flex-1 h-2.5 rounded-full overflow-hidden ${isCritical ? 'bg-slate-700' : 'bg-slate-100'}`}>
                              <div className="h-full bg-green-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.value / 5) * 100}%` }}></div>
                            </div>
                            <span className={`w-10 text-right font-semibold ${isCritical ? 'text-slate-300' : 'text-slate-500'}`}>{chartDetails.value}/5</span>
                          </div>

                          <div className="flex items-center text-sm">
                            <span className={`w-20 font-medium ${isCritical ? 'text-slate-400' : 'text-slate-600'}`}>{translations[lang].categoryService}</span>
                            <div className={`flex-1 h-2.5 rounded-full overflow-hidden ${isCritical ? 'bg-slate-700' : 'bg-slate-100'}`}>
                              <div className="h-full bg-blue-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.service / 5) * 100}%` }}></div>
                            </div>
                            <span className={`w-10 text-right font-semibold ${isCritical ? 'text-slate-300' : 'text-slate-500'}`}>{chartDetails.service}/5</span>
                          </div>

                          <div className="flex items-center text-sm">
                            <span className={`w-20 font-medium ${isCritical ? 'text-slate-400' : 'text-slate-600'}`}>{translations[lang].categoryTime}</span>
                            <div className={`flex-1 h-2.5 rounded-full overflow-hidden ${isCritical ? 'bg-slate-700' : 'bg-slate-100'}`}>
                              <div className="h-full bg-purple-500 rounded-full transition-all duration-1000" style={{ width: `${(chartDetails.time / 5) * 100}%` }}></div>
                            </div>
                            <span className={`w-10 text-right font-semibold ${isCritical ? 'text-slate-300' : 'text-slate-500'}`}>{chartDetails.time}/5</span>
                          </div>

                        </div>
                      </div>
                    )}
                  </section>

                  {/* 💡 고급 검색 토글 & 다시 검색 버튼 영역 */}
                  <div className="flex flex-col gap-2">
                    
                    {/* 카카오 데이터가 있고, 현재 뷰가 기본(구글) 뷰일 때 고급 검색 버튼 표시 */}
                    {hasAdvanced && !isAdvancedView && (
                      <button
                        type="button"
                        onClick={() => {
                          setRealScore(kakaoData.realScore ?? 0);
                          setEventProb(kakaoData.eventProbability ?? 0);
                          setAiSummary(kakaoData.aiSummary ?? "");
                          setChartDetails(kakaoData.details ?? {taste:0, value:0, service:0, time:0});
                          setIsAdvancedView(true);
                        }}
                        className="w-full rounded-xl border border-amber-500 bg-amber-500 px-4 py-3 text-sm font-bold text-white shadow-md transition hover:bg-amber-600 active:scale-95 animate-in zoom-in"
                      >
                        {translations[lang].advancedButton}
                      </button>
                    )}
                    
                    {!hasAdvanced && (
                      <div className="w-full rounded-xl border border-dashed border-slate-300 bg-slate-50/80 px-4 py-3 text-sm font-medium text-slate-500 text-center shadow-sm mt-2">
                        ⏳ {lang === "ko" 
                          ? "고급 검색 준비 중 (약 30초 후 다시 검색해주세요)" 
                          : "Preparing deep analysis (Search again in 30s)"}
                      </div>
                    )}

                    {/* 현재 뷰가 고급 뷰일 때, 다시 기본(구글) 뷰로 돌아가는 버튼 표시 */}
                    {isAdvancedView && (
                      <button
                        type="button"
                        onClick={() => {
                          if (basicData) {
                            setRealScore(basicData.score);
                            setEventProb(basicData.eProb);
                            setAiSummary(basicData.summary);
                            setChartDetails(basicData.details);
                          }
                          setIsAdvancedView(false);
                        }}
                        className={`w-full rounded-xl border px-4 py-3 text-sm font-bold shadow-sm transition active:scale-95 ${
                          isCritical 
                            ? 'bg-slate-700 border-slate-600 text-slate-200 hover:bg-slate-600' 
                            : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
                        }`}
                      >
                        {translations[lang].returnBasic}
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery("");
                        setShowResult(false);
                      }}
                      className={`w-full rounded-xl border px-4 py-3 text-sm font-medium transition shadow-sm mt-2 ${
                        isCritical 
                          ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700' 
                          : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      {translations[lang].searchAgain}
                    </button>
                  </div>

                </div>
              </div>

              <div className={`mt-8 px-6 py-4 border-t ${isCritical ? 'bg-slate-900 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                <p className={`text-[10px] leading-relaxed break-keep ${isCritical ? 'text-slate-500' : 'text-slate-400'}`}>
                  {translations[lang].disclaimer}
                </p>
              </div>
            </section>
          ) : !isAnalyzing ? (
            <div className="flex flex-col items-center justify-start w-full transition-all mt-12"> 
              
              <header className="mb-12 text-center relative z-10">
                <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl mb-4 text-slate-900">
                  {translations[lang].heroTitle}
                </h1>
                <p className="text-lg sm:text-xl text-slate-500 font-medium leading-relaxed">
                  {translations[lang].heroSubtitle}
                </p>
              </header>

              <div className="relative w-full max-w-2xl">
                <span className="absolute -top-14 -left-28 text-7xl animate-bounce duration-[1200ms] select-none cursor-default drop-shadow-xl z-0">
                  🍜
                </span>
                <span className="absolute -top-10 -right-28 text-7xl animate-bounce duration-[1500ms] delay-200 select-none cursor-default drop-shadow-xl z-0">
                  🍔
                </span>

                <div className="absolute top-20 -left-24 w-12 h-12 flex items-center justify-center group/pizza z-[50]">
                  <span className="text-4xl opacity-70 transition-transform duration-[6000ms] ease-linear pointer-events-none group-hover/pizza:scale-[80] group-hover/pizza:opacity-100 group-hover/pizza:z-[100] select-none origin-center">
                    🍕
                  </span>
                </div>

                <div className="absolute top-24 -right-24 w-12 h-12 flex items-center justify-center group/sushi z-[50]">
                  <span className="text-4xl opacity-70 transition-transform duration-[7000ms] ease-linear pointer-events-none group-hover/sushi:scale-[80] group-hover/sushi:opacity-100 group-hover/sushi:z-[100] select-none origin-center">
                    🍣
                  </span>
                </div>

                <section className="w-full rounded-3xl border border-slate-200 bg-white px-6 py-8 shadow-2xl relative z-10">
                  <form className="flex flex-col gap-4 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
                    <label className="flex-1">
                      <span className="mb-3 block text-sm font-bold text-slate-700 ml-1">{translations[lang].searchLabel}</span>
                      <div className="relative">
                        <span className="pointer-events-none absolute inset-y-0 left-4 flex items-center text-slate-400">
                          <Search className="h-5 w-5" />
                        </span>
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(event) => setSearchQuery(event.target.value)}
                          placeholder={translations[lang].searchPlaceholder}
                          className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-12 py-4 text-base text-slate-900 placeholder:text-slate-400 outline-none ring-0 transition focus:border-slate-600 focus:bg-white"
                        />
                      </div>
                    </label>
                    <button
                      type="submit"
                      disabled={!searchQuery.trim() || isSearching}
                      className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-8 py-4 text-lg font-bold text-white shadow-lg transition hover:bg-slate-800 active:scale-95 disabled:bg-slate-300 sm:min-w-[140px]"
                    >
                      {isSearching ? translations[lang].searching : translations[lang].searchButton}
                    </button>
                  </form>

                  <p className="mt-4 text-xs text-center text-slate-400">
                    {translations[lang].recentHint}
                  </p>

                  {searchResults.length > 0 && (
                    <div className="border-t border-slate-100 pt-4 mt-4 text-left">
                      <p className="mb-2 text-xs font-medium text-slate-500">{translations[lang].searchResultsTitle}</p>
                      <div className="max-h-64 overflow-y-auto pr-1">
                        <ul className="space-y-2">
                          {searchResults.map((place) => (
                            <li key={`${place.name}-${place.address}`}>
                              <button
                                type="button"
                                onClick={() => handleAnalyzePlace(place)}
                                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-800 transition hover:bg-slate-100"
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
              </div>
            </div> 
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
    </>
  );
}