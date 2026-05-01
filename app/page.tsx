"use client";
import { useEffect, useState } from "react";
import { Loader2, Search, Map } from "lucide-react";
import MapOverlay from "./MapOverlay";
import PlanBSection from "./PlanBSection";
import type { PlanBPayload } from "./PlanBSection";
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
    /** 고급 화면 축하 배너 (심층 realScore ≥ 3.5) */
    kakaoTrophyBanner: string;
    kakaoFlagBanner: string;
    kakaoTrophyNotification: string;
    kakaoFlagNotification: string;
    advancedSearchWaiting: string;
    mapViewButton: string;
    mapOverlayLoading: string;
    mapOverlayLoadError: string;
    mapOverlayFindFlags: string;
    mapOverlaySearchPlaceholder: string;
    mapOverlaySearchNoResults: string;
    mapOverlayGeolocationError: string;
    planBSectionBadge: string;
    planBFootnote: string;
    planBComingSoon: string;
    advancedDeepFactTitle: string;
    matchVerificationCaption: string;
    advancedAnalyzeFailedTitle: string;
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
    kakaoTrophyBanner: "황금 트로피 획득! 전국구 인생 맛집 등극!",
    kakaoFlagBanner: "검증된 맛집 깃발 획득! 실패 없는 맛집 등극!",
    kakaoTrophyNotification:
      "🏆 고급 분석 완료: 4.0점 이상 황금 트로피 식당으로 확인되었습니다!",
    kakaoFlagNotification:
      "🚩 고급 분석 완료: 3.5점 이상 검증된 맛집으로 확인되었습니다!",
    advancedSearchWaiting: "조금만 기다려주세요. 20초 내에 고급 검색 결과가 나옵니다.",
    mapViewButton: "지도 보기",
    mapOverlayLoading: "지도를 불러오는 중…",
    mapOverlayLoadError: "지도 로딩 실패! API 키를 확인해주세요.",
    mapOverlayFindFlags: "이 근처 깃발 찾기 🚩",
    mapOverlaySearchPlaceholder: "동네 이름 검색 (예: 연남동, 홍대)",
    mapOverlaySearchNoResults: "해당 지역을 찾을 수 없습니다.",
    mapOverlayGeolocationError: "위치 정보를 가져올 수 없습니다.",
    planBSectionBadge: "Plan B · 상황 맞춤 대체 추천",
    planBFootnote: "실제 근처 검색·DB 연동은 곧 이 버튼에 연결될 예정입니다.",
    planBComingSoon: "준비 중입니다. 다음 업데이트에서 만나요!",
    advancedDeepFactTitle: "현지 로컬 DB 심층 팩트 체크",
    matchVerificationCaption: "현지 로컬 DB 검증 기준:",
    advancedAnalyzeFailedTitle: "심층 분석을 완료할 수 없습니다",
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
    kakaoTrophyBanner: "Gold trophy earned! A national-tier, life-changing spot!",
    kakaoFlagBanner: "Verified map flag earned! A reliable, no-fail pick!",
    kakaoTrophyNotification:
      "🏆 Advanced analysis complete: scored 4.0+ — a gold-trophy level spot!",
    kakaoFlagNotification:
      "🚩 Advanced analysis complete: scored 3.5+ — a verified pick!",
    advancedSearchWaiting: "Please wait. Deep analysis results usually appear within 20 seconds.",
    mapViewButton: "View map",
    mapOverlayLoading: "Loading map…",
    mapOverlayLoadError: "Map failed to load. Please check your API key.",
    mapOverlayFindFlags: "Find nearby flags 🚩",
    mapOverlaySearchPlaceholder: "Search area (e.g. Yeonnam, Hongdae)",
    mapOverlaySearchNoResults: "That area could not be found.",
    mapOverlayGeolocationError: "Could not read your location.",
    planBSectionBadge: "Plan B · situational picks",
    planBFootnote: "Nearby verified search will plug into this button in a future update.",
    planBComingSoon: "Coming soon in a future release.",
    advancedDeepFactTitle: "Deep fact check (local review DB)",
    matchVerificationCaption: "Local DB verification basis:",
    advancedAnalyzeFailedTitle: "Advanced analysis unavailable",
  },
};

/** 플랫폼 이름이 섞일 수 있는 백엔드 reason 문자열을 UI 표시용으로 마스킹 */
function maskBackendReason(reason: unknown): string {
  let s =
    typeof reason === "string" ? reason : reason != null ? String(reason) : "";
  if (!s.trim()) return "";
  s = s.replace(/카카오맵/g, "로컬 데이터").replace(/카카오/g, "현지 리뷰");
  return s;
}

/** 고급 분석 트로피/깃발 알림을 React Strict Mode 이중 effect에서도 1회만 (같은 식당+세션) */
let kakaoTrophyFlagAlertKey: string | null = null;

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
  const [kakaoPollEnabled, setKakaoPollEnabled] = useState(false);
  const [planB, setPlanB] = useState<PlanBPayload | null>(null);

  const isCritical = showResult && realScore !== null && realScore <= 2.4;

  const googleScore = basicData?.score ?? 0;
  const kakaoScore = kakaoData?.realScore ?? 0;
  const scoreDiff = parseFloat((googleScore - kakaoScore).toFixed(1));

  /** EN + 고급 뷰: 로마자/번역 이름(지도·깃발 레이블과 동일 규칙) */
  const advancedEnPlaceLabel =
    lang === "en" && isAdvancedView && hasAdvanced && kakaoData
      ? [kakaoData?.romanizedName, kakaoData?.translatedName, basicData?.translatedName]
          .map((s: unknown) => (typeof s === "string" ? s.trim() : ""))
          .find((s) => s.length > 0) ?? ""
      : "";


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

  // 카카오 심층 분석이 백그라운드에서 끝날 때까지 주기적으로 캐시를 확인 (일일 한도 API 호출에만 집계)
  useEffect(() => {
    if (!kakaoPollEnabled || hasAdvanced || !showResult || !selectedPlace) return;

    const API = "https://gunbbang-backend.onrender.com/api/analyze";
    const { name, address } = selectedPlace;
    const maxAttempts = 36;
    let attempts = 0;
    let cancelled = false;

    const tryFetchKakao = async () => {
      if (cancelled) return;
      attempts += 1;
      if (attempts > maxAttempts) {
        setKakaoPollEnabled(false);
        return;
      }
      try {
        const response = await fetch(API, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: name, address, lang }),
        });
        if (response.status === 429 || !response.ok) return;
        const data = await response.json();
        const kd = data.kakao_data;
        if (kd?.status === "error") {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          return;
        }
        if (data.has_advanced && kd) {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          setPlanB({
            tags: Array.isArray(data.tags) ? data.tags : [],
            romanized_food_for_ui: Array.isArray(data.romanized_food_for_ui)
              ? data.romanized_food_for_ui
              : [],
            alternative_query: data.alternative_query ?? null,
          });
        }
      } catch {
        /* keep polling */
      }
    };

    const t0 = setTimeout(() => {
      void tryFetchKakao();
    }, 3000);
    const id = setInterval(() => {
      void tryFetchKakao();
    }, 5000);

    return () => {
      cancelled = true;
      clearTimeout(t0);
      clearInterval(id);
    };
  }, [kakaoPollEnabled, hasAdvanced, showResult, selectedPlace, lang]);

  // 트로피/깃발 알림·confetti·로컬 카운트: 고급 점수 기준, 식당당 1회
  useEffect(() => {
    if (!hasAdvanced || !kakaoData || !selectedPlace) return;
    if (kakaoData.status === "error") return;
    const ks = Number(kakaoData.realScore);
    if (Number.isNaN(ks) || ks < 3.5) return;

    const key = `kakao::${selectedPlace.name}::${selectedPlace.address}`;
    if (kakaoTrophyFlagAlertKey === key) return;
    kakaoTrophyFlagAlertKey = key;

    if (ks >= 4.0) {
      confetti({
        particleCount: 200,
        spread: 120,
        origin: { y: 0.6 },
        colors: ["#FFD700", "#FFA500", "#FF8C00"],
      });
      setGoldFlags((prev) => {
        const next = prev + 1;
        try {
          localStorage.setItem("jjin-view:goldFlags", next.toString());
        } catch { }
        return next;
      });
      alert(translations[lang].kakaoTrophyNotification);
    } else {
      confetti({
        particleCount: 100,
        spread: 80,
        origin: { y: 0.6 },
        colors: ["#FF0000", "#FFFFFF", "#FFB6C1"],
      });
      setRedFlags((prev) => {
        const next = prev + 1;
        try {
          localStorage.setItem("jjin-view:redFlags", next.toString());
        } catch { }
        return next;
      });
      alert(translations[lang].kakaoFlagNotification);
    }
  }, [hasAdvanced, kakaoData, selectedPlace, lang]);

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
    setKakaoPollEnabled(false);
    setPlanB(null);
    kakaoTrophyFlagAlertKey = null;

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
    if (userDailyCount >= 15) {
      alert(translations[lang].limitExceeded);
      return;
    }

    setSelectedPlace(place);
    setIsAnalyzing(true);
    kakaoTrophyFlagAlertKey = null;
    setKakaoPollEnabled(false);

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
          setKakaoPollEnabled(false);
          setIsAnalyzing(false);
          setShowResult(false);
          return;
        }

        if (!response.ok) throw new Error("Analyze response not ok");

        const data = await response.json();
        console.log("🤖 AI가 보낸 원본 데이터:", data);

        // 일일 에너지: Mongo 캐시 히트(isNewDiscovery === false)에는 차감하지 않음. 신규 AI 분석만 1회 차감.
        if (data.isNewDiscovery === true) {
          const newCount = userDailyCount + 1;
          setUserDailyCount(newCount);
          const today = new Date().toLocaleDateString();
          localStorage.setItem("zzinview_usage", JSON.stringify({ date: today, count: newCount }));
        }

        const score = data.realScore ?? data.score ?? 0;
        const eProb = data.eventProbability ?? 0;
        const summary = data.aiSummary ?? translations[lang].missingSummaryFallback;
        const details = data.details ?? { taste: 0, value: 0, service: 0, time: 0 };

        // 💡 1. 기본 데이터 세팅 & 백업
        setRealScore(score);
        setEventProb(eProb);
        setAiSummary(summary);
        setChartDetails(details);
        setBasicData({
          score,
          eProb,
          summary,
          details,
          translatedName: data.translatedName as string | undefined,
        });

        setPlanB({
          tags: Array.isArray(data.tags) ? data.tags : [],
          romanized_food_for_ui: Array.isArray(data.romanized_food_for_ui)
            ? data.romanized_food_for_ui
            : [],
          alternative_query: data.alternative_query ?? null,
        });

        // 💡 2. 고급 심층 데이터: 즉시·오류·성공 또는 백그라운드 폴링
        const kd = data.kakao_data as Record<string, unknown> | undefined;
        if (kd?.status === "error") {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
        } else if (data.has_advanced && kd) {
          setHasAdvanced(true);
          setKakaoData(kd);
          setKakaoPollEnabled(false);
        } else {
          setHasAdvanced(false);
          setKakaoData(null);
          setKakaoPollEnabled(true);
        }

        setIsAnalyzing(false);
        setShowResult(true);
      } catch (error) {
        console.error(error);
        alert(translations[lang].analyzeError);
        setKakaoPollEnabled(false);
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
      {isMapOpen && (
        <MapOverlay
          onClose={() => setIsMapOpen(false)}
          preferRomanizedLabels={lang === "en" && isAdvancedView}
          labels={{
            loading: translations[lang].mapOverlayLoading,
            loadError: translations[lang].mapOverlayLoadError,
            findFlags: translations[lang].mapOverlayFindFlags,
            searchPlaceholder: translations[lang].mapOverlaySearchPlaceholder,
            searchNoResults: translations[lang].mapOverlaySearchNoResults,
            geolocationError: translations[lang].mapOverlayGeolocationError,
          }}
        />
      )}

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
                {translations[lang].mapViewButton}
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
                      {/* 💡 뱃지 */}
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium border mb-4 ${
                        isAdvancedView 
                          ? 'bg-amber-100 text-amber-800 border-amber-300' 
                          : isCritical ? 'bg-emerald-900/30 text-emerald-400 border-emerald-800' : 'bg-emerald-50 text-emerald-700 border-emerald-100'
                      }`}>
                        {isAdvancedView ? translations[lang].advancedStatus : translations[lang].statusDone}
                      </span>
                      {advancedEnPlaceLabel ? (
                        <p className={`mt-2 text-base font-semibold tracking-tight ${isCritical ? "text-slate-200" : "text-slate-800"}`}>
                          {advancedEnPlaceLabel}
                        </p>
                      ) : null}

                      {/* 💡 1. 가짜 리뷰 정황 경고 (오직 '기본 검색' 화면에서만 뜸!) */}
                      {!isAdvancedView && eventProb >= 70 && (
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

                      {/* 💡 2. 고급 검색 점수 차이 안내 (오직 '기본 검색' 화면에 카카오 데이터가 도착했을 때만 뜸!) */}
                      {!isAdvancedView && kakaoData && (
                        <>
                          {scoreDiff >= 1.0 && (
                            <div className="mb-6 rounded-xl border-2 border-red-400 bg-red-50 px-4 py-3 text-red-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xl">🚨</span>
                                <p className="text-sm font-bold">고급 분석 결과와 {scoreDiff.toFixed(1)}점 차이가 납니다.</p>
                              </div>
                            </div>
                          )}
                          {scoreDiff >= 0.6 && scoreDiff < 1.0 && (
                            <div className="mb-6 rounded-xl border-2 border-amber-400 bg-amber-50 px-4 py-3 text-amber-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xl">⚠️</span>
                                <p className="text-sm font-bold">고급 분석 결과와 {scoreDiff.toFixed(1)}점 차이가 납니다.</p>
                              </div>
                            </div>
                          )}
                          {scoreDiff < 0 && (
                            <div className="mb-6 rounded-xl border-2 border-blue-400 bg-blue-50 px-4 py-3 text-blue-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-start sm:items-center gap-2.5">
                                <span className="text-xl mt-0.5 sm:mt-0">💎</span>
                                <div>
                                  <p className="text-sm font-bold">고급 분석 결과, 실사용자 평점이 오히려 더 높습니다.</p>
                                </div>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {isAdvancedView &&
                      kakaoData &&
                      kakaoData.status !== "error" &&
                      Number(kakaoData.realScore) >= 3.5 && (
                        <div
                          className={`mb-4 flex w-full items-center justify-center gap-2.5 rounded-2xl border px-4 py-3.5 text-center text-sm font-bold leading-snug shadow-md animate-in slide-in-from-top duration-700 ${
                            Number(kakaoData.realScore) >= 4.0
                              ? "border-amber-300/80 bg-gradient-to-r from-amber-200 via-yellow-300 to-amber-300 text-amber-950"
                              : "border-slate-300/80 bg-gradient-to-r from-slate-400 to-slate-500 text-white"
                          }`}
                        >
                          <span className="text-2xl shrink-0" aria-hidden>
                            {Number(kakaoData.realScore) >= 4.0 ? "🏆" : "🚩"}
                          </span>
                          <span>
                            {Number(kakaoData.realScore) >= 4.0
                              ? translations[lang].kakaoTrophyBanner
                              : translations[lang].kakaoFlagBanner}
                          </span>
                        </div>
                      )}

                    {/* 💡 거대한 숫자 점수 UI */}
                    {typeof realScore === "number" && (
                      <div className="flex flex-col items-center justify-center mt-6 mb-6 animate-in fade-in duration-700">
                        <div className="text-7xl font-black tracking-tighter text-slate-800 flex items-baseline gap-2">
                          {realScore.toFixed(1)}
                        </div>
                      </div>
                    )}
                  </header>

                  <section className="space-y-6">
                    {isAdvancedView && kakaoData?.status === "error" ? (
                      <div
                        className={`rounded-2xl border px-4 py-4 text-sm ${
                          isCritical
                            ? "border-amber-800/70 bg-amber-950/30 text-amber-100"
                            : "border-amber-200 bg-amber-50 text-amber-950"
                        }`}
                        role="alert"
                      >
                        <p className="mb-2 text-xs font-bold flex items-start gap-2">
                          <span className="text-lg leading-none shrink-0" aria-hidden>
                            ⚠️
                          </span>
                          <span>{translations[lang].advancedAnalyzeFailedTitle}</span>
                        </p>
                        <p className="leading-relaxed pl-[1.75rem] text-sm whitespace-pre-wrap break-keep">
                          {maskBackendReason(
                            typeof kakaoData.reason === "string"
                              ? kakaoData.reason
                              : "",
                          )}
                        </p>
                      </div>
                    ) : (
                      <div
                        className={`rounded-2xl border px-4 py-4 text-sm ${
                          isCritical
                            ? "bg-blue-950/30 border-blue-900/50 text-slate-300"
                            : "bg-blue-50/50 border-blue-100 text-slate-700"
                        }`}
                      >
                        <p
                          className={`mb-2 text-xs font-bold flex items-center gap-1 ${isCritical ? "text-blue-400" : "text-blue-600"}`}
                        >
                          <span>{isAdvancedView ? "🔥" : "🤖"}</span>
                          {isAdvancedView
                            ? translations[lang].advancedDeepFactTitle
                            : translations[lang].aiSummaryTitle}
                        </p>
                        <p className="leading-relaxed whitespace-pre-wrap transition-all duration-500">
                          {aiSummary}
                        </p>
                      </div>
                    )}

                    {isAdvancedView &&
                      chartDetails &&
                      kakaoData?.status !== "error" && (
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

                    {isAdvancedView &&
                      kakaoData?.status !== "error" &&
                      (String(kakaoData?.kakao_matched_name ?? "").trim() !== "" ||
                        String(kakaoData?.kakao_matched_address ?? "").trim() !==
                          "") && (
                      <p
                        className="text-[11px] leading-snug text-slate-500"
                      >
                        <span aria-hidden>🔍</span>{" "}
                        <span>{translations[lang].matchVerificationCaption}</span>{" "}
                        {(() => {
                          const mn = String(
                            kakaoData?.kakao_matched_name ?? "",
                          ).trim();
                          const ma = String(
                            kakaoData?.kakao_matched_address ?? "",
                          ).trim();
                          if (mn && ma) return `${mn} (${ma})`;
                          return mn || ma;
                        })()}
                      </p>
                    )}
                  </section>

                  {/* 💡 고급 검색 토글 & 다시 검색 버튼 영역 */}
                  <div className="flex flex-col gap-2">
                    
                    {/* 카카오 데이터가 있고, 현재 뷰가 기본(구글) 뷰일 때 고급 검색 버튼 표시 */}
                    {hasAdvanced && !isAdvancedView && (
                      <button
                        type="button"
                        onClick={() => {
                          if (kakaoData?.status === "error") {
                            setIsAdvancedView(true);
                            return;
                          }
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
                        ⏳ {translations[lang].advancedSearchWaiting}
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

                  {planB?.alternative_query != null &&
                    typeof planB.alternative_query.suggest_message === "string" &&
                    planB.alternative_query.suggest_message.trim() !== "" && (
                    <PlanBSection
                      lang={lang}
                      data={planB}
                      isCritical={!!isCritical}
                      labels={{
                        badge: translations[lang].planBSectionBadge,
                        footnote: translations[lang].planBFootnote,
                        comingSoon: translations[lang].planBComingSoon,
                      }}
                    />
                  )}

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