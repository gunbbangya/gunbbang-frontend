"use client";
import { useEffect, useState } from "react";
import { Loader2, Map, ChevronLeft } from "lucide-react";
import MapOverlay from "./MapOverlay";
import PlanBSection from "./PlanBSection";
import type { PlanBPayload } from "./PlanBSection";
import confetti from "canvas-confetti";

type Lang = "ko" | "en";

const LANG_STORAGE_KEY = "jjin-view:lang";

const API_BASE =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "https://gunbbang-backend.onrender.com";

const PURPOSE_VALUES = [
  "solo",
  "date",
  "group",
  "foreignerFriendly",
  "lowRisk",
  "quickMeal",
] as const;

function getDecisionDisplayLabel(value: unknown, lang: Lang): string {
  const raw = String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "_");
  if (lang === "en") {
    if (raw === "INSUFFICIENT_DATA") return "INSUFFICIENT DATA";
    return raw || "—";
  }
  const ko: Record<string, string> = {
    GO: "추천",
    OK: "무난함",
    CAUTION: "주의",
    AVOID: "피하는 편이 좋음",
    INSUFFICIENT_DATA: "정보 부족",
  };
  return ko[raw] || raw || "—";
}

function getRiskTypeLabel(value: unknown, lang: Lang): string {
  const t = String(value ?? "").trim().toLowerCase();
  if (lang === "en") {
    const en: Record<string, string> = {
      waiting: "Waiting",
      service: "Service",
      hygiene: "Hygiene",
      price: "Price",
      taste: "Taste",
      ordering: "Ordering",
      crowding: "Crowding",
      tourist_trap: "Tourist trap risk",
      data_limit: "Data limitation",
    };
    return en[t] || t;
  }
  const ko: Record<string, string> = {
    waiting: "대기",
    service: "서비스",
    hygiene: "위생",
    price: "가격",
    taste: "맛",
    ordering: "주문 난이도",
    crowding: "혼잡",
    tourist_trap: "관광객 낚시 위험",
    data_limit: "데이터 한계",
  };
  return ko[t] || t;
}

function getRiskLevelLabel(value: unknown, lang: Lang): string {
  const lv = String(value ?? "").trim().toLowerCase();
  if (lang === "en") {
    if (lv === "high") return "High";
    if (lv === "medium") return "Medium";
    if (lv === "low") return "Low";
    return lv || "—";
  }
  if (lv === "high") return "높음";
  if (lv === "medium") return "보통";
  if (lv === "low") return "낮음";
  return lv || "—";
}

function getPurposeLabel(value: string, lang: Lang): string {
  const v = value.trim();
  if (lang === "en") {
    const en: Record<string, string> = {
      solo: "Solo",
      date: "Date",
      group: "Group",
      foreignerFriendly: "Foreigner-friendly",
      lowRisk: "Low-risk",
      quickMeal: "Quick meal",
    };
    return en[v] || v;
  }
  const ko: Record<string, string> = {
    solo: "혼밥",
    date: "데이트",
    group: "단체",
    foreignerFriendly: "외국인 친화",
    lowRisk: "실패 확률 낮음",
    quickMeal: "빠른 식사",
  };
  return ko[v] || v;
}

function getPracticalFieldLabel(key: string, lang: Lang): string {
  if (lang === "en") {
    const map: Record<string, string> = {
      waiting: "Waiting",
      parking: "Parking",
      soloFriendly: "Solo-friendly",
      groupFriendly: "Group-friendly",
      dateFriendly: "Date-friendly",
      foreignerAccess: "Foreigner access",
      orderingDifficulty: "Ordering difficulty",
      englishMenu: "English menu",
      bestTimeToVisit: "Best time to visit",
    };
    return map[key] || key;
  }
  const map: Record<string, string> = {
    waiting: "대기",
    parking: "주차",
    soloFriendly: "혼밥",
    groupFriendly: "단체",
    dateFriendly: "데이트",
    foreignerAccess: "외국인 접근",
    orderingDifficulty: "주문 난이도",
    englishMenu: "영어 메뉴",
    bestTimeToVisit: "추천 시간대",
  };
  return map[key] || key;
}

function getConfidenceLevelLabel(value: unknown, lang: Lang): string {
  return getRiskLevelLabel(value, lang);
}

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
    advancedAnalyzeFailedTitle: string;
    advancedAnalyzeInsufficientBody: string;
    kakaoSourceSearchPlace: string;
    kakaoSourceReviewOrigin: string;
    kakaoSourceAddress: string;
    kakaoSourceKakaoRating: string;
    kakaoSourceKakaoTotalReviews: string;
    kakaoSourceReviewsAnalyzed: string;
    kakaoSourceReviewsUsed: string;
    kakaoSourceStatUnavailable: string;
    kakaoSourceFallbackUnstable: string;
    advancedVerifiedBadge: string;
    advancedBasicOnlyBadge: string;
    advancedPendingBadge: string;
    advancedEvidenceLine: string;
    advancedBasicOnlyMessage: string;
    cardDecision: string;
    cardBestFor: string;
    cardAvoidIf: string;
    cardMustKnow: string;
    cardRiskFlags: string;
    cardPractical: string;
    cardFoodSignals: string;
    cardNearbySafer: string;
    cardNoAlternatives: string;
    kakaoSourceLastAnalyzed: string;
    importanceHigh: string;
    importanceMedium: string;
    importanceLow: string;
    homeFindTitle: string;
    homeFindDesc: string;
    homeCheckTitle: string;
    homeCheckDesc: string;
    homeSubtitle: string;
    findFlowTitle: string;
    findAreaLabel: string;
    findAreaPlaceholder: string;
    findCategoryLabel: string;
    findCategoryPlaceholder: string;
    findPurposeLabel: string;
    findPurposeAny: string;
    findSubmit: string;
    findLoading: string;
    findVisitSafetyLabel: string;
    findConfidenceLabel: string;
    findUsedReviewsLabel: string;
    checkFlowTitle: string;
    checkCandidateHint: string;
    checkRestaurantNameLabel: string;
    checkNamePlaceholder: string;
    checkFindCandidatesButton: string;
    candidateGoogleRatingLine: string;
    candidateReviewsWord: string;
    limitedScanHeadline: string;
    limitedScanLine1: string;
    limitedScanLine2: string;
    limitedScanLine3: string;
    verifiedAdvancedHeadline: string;
    verifiedAdvancedLine1: string;
    basicSnippetBadge: string;
    scoreDiffHigh: string;
    scoreDiffMed: string;
    scoreDiffLow: string;
    criticalScoreBanner: string;
    visitSafetyMetricLabel: string;
    limitedGoogleReferenceLabel: string;
    approxMetersLabel: string;
    confidenceReasonLabel: string;
    cardDataLimitationsTitle: string;
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
    returnBasic: "↩️ 제한된 장소 확인(참고) 보기로",
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
    advancedAnalyzeFailedTitle: "심층 분석을 완료할 수 없습니다",
    advancedAnalyzeInsufficientBody:
      "현지 데이터가 부족하거나, 식당 방침으로 후기를 제공하지 않는 곳입니다.",
    kakaoSourceSearchPlace: "검색 가게",
    kakaoSourceReviewOrigin: "리뷰 출처",
    kakaoSourceAddress: "주소",
    kakaoSourceKakaoRating: "현지 평점",
    kakaoSourceKakaoTotalReviews: "현지 전체 리뷰 수",
    kakaoSourceReviewsAnalyzed: "분석 리뷰",
    kakaoSourceReviewsUsed: "사용 리뷰",
    kakaoSourceStatUnavailable: "확인 불가",
    kakaoSourceFallbackUnstable:
      "후기(li) 단위 수집이 불안정했을 수 있어요. 점수·요약 해석 시 참고해 주세요.",
    advancedVerifiedBadge: "검증된 심층 분석",
    advancedBasicOnlyBadge: "기본 스캔만",
    advancedPendingBadge: "고급 분석 대기 중",
    advancedEvidenceLine:
      "카카오 리뷰 기준: 모델에 반영된 리뷰 {used}개 · 마지막 분석 {when}",
    advancedBasicOnlyMessage: "이 장소는 아직 고급 분석 결과가 준비되지 않았습니다.",
    cardDecision: "방문 결정",
    cardBestFor: "이런 분께 추천",
    cardAvoidIf: "이런 분은 피하세요",
    cardMustKnow: "가기 전에 꼭 알 것",
    cardRiskFlags: "리스크 신호",
    cardPractical: "실전 정보",
    cardFoodSignals: "메뉴·맛 신호",
    cardNearbySafer: "근처 더 안전한 대안",
    cardNoAlternatives: "조건에 맞는 사전 분석 대안이 아직 없습니다.",
    kakaoSourceLastAnalyzed: "마지막 분석 시각",
    importanceHigh: "높음",
    importanceMedium: "보통",
    importanceLow: "낮음",
    homeFindTitle: "맛집 찾기",
    homeFindDesc: "지역과 음식 종류를 고르면, 미리 검증된 가게를 보여드려요.",
    homeCheckTitle: "맛집 검증하기",
    homeCheckDesc:
      "가려는 식당명을 입력하면, 리뷰 리스크와 근처 대안을 분석해드려요.",
    homeSubtitle: "검증된 심층 분석과 제한된 장소 확인을 구분합니다.",
    findFlowTitle: "검증된 식당 찾기",
    findAreaLabel: "지역",
    findAreaPlaceholder: "지역 예시: 연남동, 홍대, 강남구",
    findCategoryLabel: "음식 종류 (선택)",
    findCategoryPlaceholder: "음식 종류 선택: 삼겹살, 한식, 라멘, 치킨, 카페",
    findPurposeLabel: "목적 (선택)",
    findPurposeAny: "선택 안 함",
    findSubmit: "검증된 가게 보기",
    findLoading: "DB에서 불러오는 중…",
    findVisitSafetyLabel: "방문 안전도",
    findConfidenceLabel: "신뢰도",
    findUsedReviewsLabel: "사용 리뷰 수",
    checkFlowTitle: "맛집 검증하기",
    checkCandidateHint:
      "식당명으로 검색해 장소 후보를 확인한 뒤, 맞는 곳을 선택하세요.",
    checkRestaurantNameLabel: "식당명",
    checkNamePlaceholder: "가려는 식당 이름을 입력하세요",
    checkFindCandidatesButton: "후보 찾기",
    candidateGoogleRatingLine: "구글 평점",
    candidateReviewsWord: "리뷰 수",
    limitedScanHeadline: "제한된 장소 확인",
    limitedScanLine1: "심층 검증을 완료하지 못했습니다.",
    limitedScanLine2: "카카오맵 리뷰가 부족하거나 접근이 제한되어 있습니다.",
    limitedScanLine3:
      "아래 정보는 장소 확인용 제한 정보이며, 방문 여부를 판단하기에는 충분하지 않습니다.",
    verifiedAdvancedHeadline: "검증된 심층 분석",
    verifiedAdvancedLine1: "카카오맵 유효 리뷰 {used}개 기준",
    basicSnippetBadge: "제한된 장소 확인 (구글 샘플)",
    scoreDiffHigh: "심층 분석 점수와 {diff}점 이상 차이가 납니다.",
    scoreDiffMed: "심층 분석 점수와 {diff}점 차이가 납니다.",
    scoreDiffLow: "심층 분석상 실제 체감 평가가 참고 점수보다 높게 나왔습니다.",
    criticalScoreBanner: "점수가 매우 낮음 — 참고용 신호로만 활용하세요.",
    visitSafetyMetricLabel: "방문 안전 점수",
    limitedGoogleReferenceLabel: "구글(참고)",
    approxMetersLabel: "약 {n}m",
    confidenceReasonLabel: "근거",
    cardDataLimitationsTitle: "데이터 한계",
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
    returnBasic: "↩️ View limited place check (reference)",
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
    advancedAnalyzeFailedTitle: "Advanced analysis unavailable",
    advancedAnalyzeInsufficientBody:
      "Insufficient local data, or the restaurant has disabled public reviews.",
    kakaoSourceSearchPlace: "Matched place",
    kakaoSourceReviewOrigin: "Review source",
    kakaoSourceAddress: "Address",
    kakaoSourceKakaoRating: "Local average rating",
    kakaoSourceKakaoTotalReviews: "Local total reviews",
    kakaoSourceReviewsAnalyzed: "Reviews analyzed",
    kakaoSourceReviewsUsed: "Reviews fed to model",
    kakaoSourceStatUnavailable: "Unavailable",
    kakaoSourceFallbackUnstable:
      "Review list capture may have been unstable (fallback). Interpret scores/summary cautiously.",
    advancedVerifiedBadge: "Verified advanced analysis",
    advancedBasicOnlyBadge: "Basic scan only",
    advancedPendingBadge: "Advanced analysis pending",
    advancedEvidenceLine:
      "Based on Kakao reviews: {used} useful reviews fed to the model · last analyzed {when}",
    advancedBasicOnlyMessage: "Advanced analysis is not available yet for this place.",
    cardDecision: "Decision",
    cardBestFor: "Best for",
    cardAvoidIf: "Avoid if",
    cardMustKnow: "Must know before going",
    cardRiskFlags: "Risk flags",
    cardPractical: "Practical info",
    cardFoodSignals: "Food signals",
    cardNearbySafer: "Nearby safer alternatives",
    cardNoAlternatives: "No precomputed alternatives matched the safety filters yet.",
    kakaoSourceLastAnalyzed: "Last analyzed at",
    importanceHigh: "High",
    importanceMedium: "Medium",
    importanceLow: "Low",
    homeFindTitle: "Find restaurants",
    homeFindDesc: "Choose an area and food type. We'll show pre-verified places.",
    homeCheckTitle: "Check a restaurant",
    homeCheckDesc:
      "Already have a place in mind? Check risks and safer nearby alternatives.",
    homeSubtitle: "We separate verified advanced analysis from limited place checks.",
    findFlowTitle: "Find verified spots",
    findAreaLabel: "Area",
    findAreaPlaceholder: "Area examples: Yeonnam-dong, Hongdae, Gangnam-gu",
    findCategoryLabel: "Food type (optional)",
    findCategoryPlaceholder: "Food type: Korean BBQ, Korean food, ramen, chicken, cafe",
    findPurposeLabel: "Purpose (optional)",
    findPurposeAny: "Any",
    findSubmit: "Show verified places",
    findLoading: "Loading from database…",
    findVisitSafetyLabel: "Visit safety",
    findConfidenceLabel: "Confidence",
    findUsedReviewsLabel: "Reviews used",
    checkFlowTitle: "Check a restaurant",
    checkCandidateHint:
      "Search by restaurant name to see place candidates, then pick the correct one.",
    checkRestaurantNameLabel: "Restaurant name",
    checkNamePlaceholder: "Enter the restaurant name",
    checkFindCandidatesButton: "Find candidates",
    candidateGoogleRatingLine: "Google rating",
    candidateReviewsWord: "reviews",
    limitedScanHeadline: "Limited place check",
    limitedScanLine1: "Advanced verification could not be completed.",
    limitedScanLine2: "Kakao reviews may be unavailable, restricted, or insufficient.",
    limitedScanLine3:
      "The information below is limited place-confirmation data and is not enough for a full visit decision.",
    verifiedAdvancedHeadline: "Verified advanced analysis",
    verifiedAdvancedLine1: "Based on {used} useful Kakao reviews",
    basicSnippetBadge: "Limited place check (Google sample)",
    scoreDiffHigh: "Deep analysis differs from the reference score by {diff}+ points.",
    scoreDiffMed: "Deep analysis differs from the reference score by {diff} points.",
    scoreDiffLow: "Deep analysis suggests on-the-ground sentiment is higher than the reference score.",
    criticalScoreBanner: "Very low score — use only as a reference signal.",
    visitSafetyMetricLabel: "Visit safety score",
    limitedGoogleReferenceLabel: "Google (reference)",
    approxMetersLabel: "~{n} m",
    confidenceReasonLabel: "Reason",
    cardDataLimitationsTitle: "Data limitations",
  },
};

function getImportanceLabel(value: unknown, lang: Lang): string {
  const t = String(value ?? "").trim().toLowerCase();
  if (t === "high") return translations[lang].importanceHigh;
  if (t === "medium") return translations[lang].importanceMedium;
  if (t === "low") return translations[lang].importanceLow;
  return t || "—";
}

/** 레거시 매칭/크롤 오류 — LIMITED_SCAN(심층 불가) 페이로드는 여기서 제외한다. */
function isKakaoDeepFailureStatus(kdOrStatus: unknown): boolean {
  if (kdOrStatus != null && typeof kdOrStatus === "object") {
    const d = kdOrStatus as Record<string, unknown>;
    if (d.displayMode === "LIMITED_SCAN" || d.analysisStatus === "advanced_unavailable") {
      return false;
    }
    const st = d.status;
    return st === "error" || st === "no_data";
  }
  const st = kdOrStatus;
  return st === "error" || st === "no_data";
}

function maskBackendReason(reason: unknown): string {
  let s =
    typeof reason === "string" ? reason : reason != null ? String(reason) : "";
  if (!s.trim()) return "";
  s = s.replace(/카카오맵/g, "로컬 데이터").replace(/카카오/g, "현지 리뷰");
  return s;
}

function formatKakaoSourceNumber(v: unknown): string | null {
  if (v === null || v === undefined || v === "") return null;
  const n = typeof v === "number" ? v : Number(v);
  if (Number.isFinite(n)) return String(n);
  return null;
}

function formatKakaoSourceRating(v: unknown, unavailable: string): string {
  if (v === null || v === undefined || v === "") return unavailable;
  const n = Number(v);
  if (!Number.isFinite(n)) return unavailable;
  return n.toFixed(1);
}

function formatIsoWhen(iso: unknown, unavailable: string): string {
  if (typeof iso !== "string" || !iso.trim()) return unavailable;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return unavailable;
  return d.toLocaleString();
}

/** 고급 분석 트로피/깃발 알림을 React Strict Mode 이중 effect에서도 1회만 (같은 식당+세션) */
let kakaoTrophyFlagAlertKey: string | null = null;

export default function HomePage() {
  const [lang, setLang] = useState<Lang>("ko");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [messageIndex, setMessageIndex] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [isMapOpen, setIsMapOpen] = useState(false);
  
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

  const [redFlags, setRedFlags] = useState(0);
  const [goldFlags, setGoldFlags] = useState(0);
  const [userDailyCount, setUserDailyCount] = useState(0);
  const [kakaoPollEnabled, setKakaoPollEnabled] = useState(false);
  const [planB, setPlanB] = useState<PlanBPayload | null>(null);
  const [advancedAnalysisStatus, setAdvancedAnalysisStatus] = useState<
    "verified_advanced" | "basic_scan_only" | "pending" | "limited_scan" | null
  >(null);

  type ProductFlow = "home" | "find" | "check";
  const [productFlow, setProductFlow] = useState<ProductFlow>("home");
  const [findArea, setFindArea] = useState("");
  const [findCategory, setFindCategory] = useState("");
  const [findPurpose, setFindPurpose] = useState("");
  const [findLoading, setFindLoading] = useState(false);
  const [findResults, setFindResults] = useState<Record<string, unknown>[]>([]);
  const [findEmptyMsg, setFindEmptyMsg] = useState<string | null>(null);

  const [checkSearchQuery, setCheckSearchQuery] = useState("");
  const [checkSearching, setCheckSearching] = useState(false);
  const [checkCandidates, setCheckCandidates] = useState<
    {
      name: string;
      address: string;
      rating?: number;
      user_ratings_total?: number;
    }[]
  >([]);

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

    const API = `${API_BASE}/api/analyze`;
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
        const isLimited =
          kd &&
          typeof kd === "object" &&
          ((kd as Record<string, unknown>).displayMode === "LIMITED_SCAN" ||
            (kd as Record<string, unknown>).analysisStatus === "advanced_unavailable" ||
            data.advancedAnalysisStatus === "limited_scan");
        if (isLimited) {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          setAdvancedAnalysisStatus("limited_scan");
          return;
        }
        if (isKakaoDeepFailureStatus(kd)) {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          setAdvancedAnalysisStatus("limited_scan");
          return;
        }
        if (data.has_advanced && kd) {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          if (
            data.advancedAnalysisStatus === "verified_advanced" ||
            data.advancedAnalysisStatus === "pending" ||
            data.advancedAnalysisStatus === "basic_scan_only" ||
            data.advancedAnalysisStatus === "limited_scan"
          ) {
            setAdvancedAnalysisStatus(data.advancedAnalysisStatus);
          } else {
            setAdvancedAnalysisStatus("verified_advanced");
          }
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
    if (advancedAnalysisStatus === "limited_scan") return;
    if (isKakaoDeepFailureStatus(kakaoData)) return;
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
        const response = await fetch(`${API_BASE}/api/analyze`, {
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
        const isLimited =
          kd &&
          (kd.displayMode === "LIMITED_SCAN" ||
            kd.analysisStatus === "advanced_unavailable" ||
            data.advancedAnalysisStatus === "limited_scan");
        if (isLimited) {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          setAdvancedAnalysisStatus("limited_scan");
        } else if (isKakaoDeepFailureStatus(kd)) {
          setKakaoData(kd);
          setHasAdvanced(true);
          setKakaoPollEnabled(false);
          setAdvancedAnalysisStatus("limited_scan");
        } else if (data.has_advanced && kd) {
          setHasAdvanced(true);
          setKakaoData(kd);
          setKakaoPollEnabled(false);
          const ast = data.advancedAnalysisStatus;
          if (
            ast === "verified_advanced" ||
            ast === "basic_scan_only" ||
            ast === "pending" ||
            ast === "limited_scan"
          ) {
            setAdvancedAnalysisStatus(ast);
          } else {
            setAdvancedAnalysisStatus("verified_advanced");
          }
        } else {
          setHasAdvanced(false);
          setKakaoData(null);
          setKakaoPollEnabled(true);
          setAdvancedAnalysisStatus("pending");
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

  const handleFindVerified = async (event: React.FormEvent) => {
    event.preventDefault();
    setFindLoading(true);
    setFindEmptyMsg(null);
    try {
      const response = await fetch(`${API_BASE}/api/find-verified`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lang,
          area: findArea.trim() || undefined,
          category: findCategory.trim() || undefined,
          purpose: findPurpose.trim() || undefined,
        }),
      });
      if (!response.ok) throw new Error("find-verified failed");
      const data: { results?: unknown[]; empty?: boolean; emptyMessage?: string } =
        await response.json();
      setFindResults(
        Array.isArray(data.results) ? (data.results as Record<string, unknown>[]) : [],
      );
      setFindEmptyMsg(data.empty ? String(data.emptyMessage || "") : null);
    } catch {
      setFindResults([]);
      setFindEmptyMsg(lang === "en" ? "Request failed." : "요청에 실패했습니다.");
    } finally {
      setFindLoading(false);
    }
  };

  const handleCheckCandidatesSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!checkSearchQuery.trim()) return;
    setCheckSearching(true);
    try {
      const params = new URLSearchParams({
        q: checkSearchQuery.trim(),
        max_results: "10",
      });
      const response = await fetch(
        `${API_BASE}/api/google-place-candidates?${params.toString()}`,
      );
      if (!response.ok) throw new Error("candidates failed");
      const rows: unknown = await response.json();
      setCheckCandidates(
        Array.isArray(rows)
          ? (rows as Record<string, unknown>[]).map((x) => ({
              name: String(x.name || ""),
              address: String(x.address || ""),
              rating: typeof x.rating === "number" ? x.rating : undefined,
              user_ratings_total:
                typeof x.user_ratings_total === "number" ? x.user_ratings_total : undefined,
            }))
          : [],
      );
    } catch {
      setCheckCandidates([]);
      alert(translations[lang].searchError);
    } finally {
      setCheckSearching(false);
    }
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
                <div className="bg-red-900/80 py-1.5 text-center text-[10px] font-black tracking-wide text-red-100 animate-pulse break-keep px-2">
                  {translations[lang].criticalScoreBanner}
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

                      {!isAdvancedView && (
                        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                          <p className="font-bold">{translations[lang].basicSnippetBadge}</p>
                          <p className="mt-1 leading-relaxed">{translations[lang].limitedScanLine3}</p>
                        </div>
                      )}

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
                      {!isAdvancedView &&
                        kakaoData &&
                        !isKakaoDeepFailureStatus(kakaoData) && (
                        <>
                          {scoreDiff >= 1.0 && (
                            <div className="mb-6 rounded-xl border-2 border-red-400 bg-red-50 px-4 py-3 text-red-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xl">🚨</span>
                                <p className="text-sm font-bold break-keep">
                                  {translations[lang].scoreDiffHigh.replace(
                                    "{diff}",
                                    scoreDiff.toFixed(1),
                                  )}
                                </p>
                              </div>
                            </div>
                          )}
                          {scoreDiff >= 0.6 && scoreDiff < 1.0 && (
                            <div className="mb-6 rounded-xl border-2 border-amber-400 bg-amber-50 px-4 py-3 text-amber-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-center gap-2.5">
                                <span className="text-xl">⚠️</span>
                                <p className="text-sm font-bold break-keep">
                                  {translations[lang].scoreDiffMed.replace(
                                    "{diff}",
                                    scoreDiff.toFixed(1),
                                  )}
                                </p>
                              </div>
                            </div>
                          )}
                          {scoreDiff < 0 && (
                            <div className="mb-6 rounded-xl border-2 border-blue-400 bg-blue-50 px-4 py-3 text-blue-800 animate-in zoom-in duration-500 shadow-sm">
                              <div className="flex items-start sm:items-center gap-2.5">
                                <span className="text-xl mt-0.5 sm:mt-0">💎</span>
                                <div>
                                  <p className="text-sm font-bold break-keep">
                                    {translations[lang].scoreDiffLow}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {!isKakaoDeepFailureStatus(kakaoData) ||
                    !isAdvancedView ? (
                      <>
                        {isAdvancedView &&
                          kakaoData &&
                          !isKakaoDeepFailureStatus(kakaoData) &&
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
                      </>
                    ) : null}
                  </header>

                  <section className="space-y-6">
                    {isAdvancedView &&
                    kakaoData &&
                    isKakaoDeepFailureStatus(kakaoData) ? (
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
                            typeof kakaoData.reason === "string" ? kakaoData.reason : "",
                          )}
                        </p>
                      </div>
                    ) : isAdvancedView &&
                      kakaoData &&
                      !isKakaoDeepFailureStatus(kakaoData) ? (
                      <div className="space-y-4">
                        <div className="flex flex-wrap gap-2">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold border ${
                              advancedAnalysisStatus === "verified_advanced"
                                ? isCritical
                                  ? "border-emerald-700 bg-emerald-950/40 text-emerald-200"
                                  : "border-emerald-200 bg-emerald-50 text-emerald-900"
                                : advancedAnalysisStatus === "limited_scan"
                                  ? isCritical
                                    ? "border-amber-800 bg-amber-950/40 text-amber-100"
                                    : "border-amber-300 bg-amber-50 text-amber-950"
                                  : advancedAnalysisStatus === "pending"
                                    ? isCritical
                                      ? "border-slate-600 bg-slate-800 text-slate-200"
                                      : "border-slate-200 bg-slate-100 text-slate-700"
                                    : isCritical
                                      ? "border-slate-600 bg-slate-900 text-slate-300"
                                      : "border-slate-200 bg-white text-slate-600"
                            }`}
                          >
                            {advancedAnalysisStatus === "verified_advanced"
                              ? translations[lang].advancedVerifiedBadge
                              : advancedAnalysisStatus === "limited_scan"
                                ? translations[lang].limitedScanHeadline
                                : advancedAnalysisStatus === "pending"
                                  ? translations[lang].advancedPendingBadge
                                  : translations[lang].advancedBasicOnlyBadge}
                          </span>
                        </div>
                        {advancedAnalysisStatus === "pending" && (
                          <p
                            className={`text-sm ${isCritical ? "text-slate-300" : "text-slate-600"}`}
                          >
                            {translations[lang].advancedBasicOnlyMessage}
                          </p>
                        )}
                        {advancedAnalysisStatus === "limited_scan" && (
                          <div
                            className={`rounded-xl border px-3 py-3 text-xs leading-relaxed ${
                              isCritical
                                ? "border-amber-800/70 bg-amber-950/30 text-amber-100"
                                : "border-amber-200 bg-amber-50 text-amber-950"
                            }`}
                          >
                            <p className="font-bold">{translations[lang].limitedScanLine1}</p>
                            <p className="mt-1">{translations[lang].limitedScanLine2}</p>
                            <p className="mt-2">{translations[lang].limitedScanLine3}</p>
                            {(() => {
                              const li = kakaoData.limitedInfo as
                                | Record<string, unknown>
                                | undefined;
                              if (!li || typeof li !== "object") return null;
                              return (
                                <dl className="mt-3 space-y-1 border-t border-amber-300/40 pt-2">
                                  <div className="flex gap-2">
                                    <dt className="opacity-80 shrink-0">
                                      {translations[lang].limitedGoogleReferenceLabel}
                                    </dt>
                                    <dd>
                                      ★{li.googleRating != null ? String(li.googleRating) : "—"} ·{" "}
                                      {translations[lang].candidateReviewsWord}{" "}
                                      {li.googleReviewCount != null ? String(li.googleReviewCount) : "—"}
                                    </dd>
                                  </div>
                                  {typeof li.placeName === "string" && li.placeName.trim() ? (
                                    <div className="flex gap-2">
                                      <dt className="opacity-80">{translations[lang].kakaoSourceSearchPlace}</dt>
                                      <dd>{li.placeName}</dd>
                                    </div>
                                  ) : null}
                                </dl>
                              );
                            })()}
                          </div>
                        )}
                        {advancedAnalysisStatus === "verified_advanced" && (
                          <p
                            className={`text-xs ${isCritical ? "text-slate-400" : "text-slate-600"}`}
                          >
                            {translations[lang].advancedEvidenceLine
                              .replace(
                                "{used}",
                                String(
                                  (kakaoData.confidence as { usedReviewCount?: unknown } | undefined)
                                    ?.usedReviewCount ??
                                    (kakaoData.sourceStats as { usedReviewCount?: unknown } | undefined)
                                      ?.usedReviewCount ??
                                    (kakaoData as { usedReviewCount?: unknown }).usedReviewCount ??
                                    "—",
                                ),
                              )
                              .replace(
                                "{when}",
                                formatIsoWhen(
                                  (kakaoData as { lastAnalyzedAt?: unknown }).lastAnalyzedAt,
                                  translations[lang].kakaoSourceStatUnavailable,
                                ),
                              )}
                          </p>
                        )}
                        {(() => {
                          const dec = (kakaoData.decision ?? {}) as Record<string, unknown>;
                          const lbl = String(dec.label ?? "").toUpperCase();
                          const decisionDisplay = getDecisionDisplayLabel(dec.label, lang);
                          const cardBase = `rounded-xl border px-3 py-3 text-sm ${
                            isCritical
                              ? "border-slate-600 bg-slate-900/60 text-slate-100"
                              : "border-slate-200 bg-white text-slate-800"
                          }`;
                          const h2 = `text-xs font-bold uppercase tracking-wide mb-2 ${
                            isCritical ? "text-slate-400" : "text-slate-500"
                          }`;
                          const who = Array.isArray(kakaoData.whoShouldGo)
                            ? (kakaoData.whoShouldGo as string[])
                            : [];
                          const avoidIf = Array.isArray(kakaoData.whoShouldAvoid)
                            ? (kakaoData.whoShouldAvoid as string[])
                            : [];
                          const mustKnow = Array.isArray(kakaoData.mustKnowBeforeGoing)
                            ? (kakaoData.mustKnowBeforeGoing as {
                                point?: string;
                                evidence?: string;
                                importance?: string;
                              }[])
                            : [];
                          const risks = Array.isArray(kakaoData.riskFlags) ? kakaoData.riskFlags : [];
                          const pi = (kakaoData.practicalInfo ?? {}) as Record<string, string>;
                          const fs = (kakaoData.foodSignals ?? {}) as Record<string, unknown>;
                          const near = Array.isArray(kakaoData.nearbySaferAlternatives)
                            ? (kakaoData.nearbySaferAlternatives as Record<string, unknown>[])
                            : [];
                          const labelColor =
                            lbl === "GO"
                              ? "text-emerald-600"
                              : lbl === "OK"
                                ? "text-blue-600"
                                : lbl === "CAUTION"
                                  ? "text-amber-600"
                                  : lbl === "AVOID"
                                    ? "text-red-600"
                                    : "text-slate-500";
                          return (
                            <div className="grid gap-3">
                              <div className={cardBase}>
                                <p className={h2}>{translations[lang].cardDecision}</p>
                                <p className={`text-2xl font-black ${labelColor}`}>
                                  {decisionDisplay}
                                </p>
                                <p className="mt-1 text-xs text-slate-500">
                                  {translations[lang].visitSafetyMetricLabel}:{" "}
                                  <span className="font-semibold">
                                    {typeof dec.visitSafetyScore === "number"
                                      ? (dec.visitSafetyScore as number).toFixed(1)
                                      : String(dec.visitSafetyScore ?? "—")}
                                  </span>
                                </p>
                                <p className="mt-2 font-medium">{String(dec.oneLine ?? "")}</p>
                                <p className="mt-1 text-xs opacity-90">{String(dec.shortReason ?? "")}</p>
                              </div>
                              {(who.length > 0 || avoidIf.length > 0) && (
                                <div className="grid gap-3 sm:grid-cols-2">
                                  {who.length > 0 ? (
                                    <div className={cardBase}>
                                      <p className={h2}>{translations[lang].cardBestFor}</p>
                                      <ul className="list-disc pl-4 space-y-1 text-xs">
                                        {who.map((x, i) => (
                                          <li key={i}>{x}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  ) : null}
                                  {avoidIf.length > 0 ? (
                                    <div className={cardBase}>
                                      <p className={h2}>{translations[lang].cardAvoidIf}</p>
                                      <ul className="list-disc pl-4 space-y-1 text-xs">
                                        {avoidIf.map((x, i) => (
                                          <li key={i}>{x}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  ) : null}
                                </div>
                              )}
                              {mustKnow.length > 0 ? (
                                <div className={cardBase}>
                                  <p className={h2}>{translations[lang].cardMustKnow}</p>
                                  <ul className="space-y-2">
                                    {mustKnow.map((m, i) => (
                                      <li
                                        key={i}
                                        className="text-xs border-b border-slate-200/30 pb-2 last:border-0"
                                      >
                                        <span className="font-semibold">{m.point}</span>{" "}
                                        <span className="opacity-80">
                                          ({getImportanceLabel(m.importance, lang)})
                                        </span>
                                        <p className="mt-0.5 opacity-90">{m.evidence}</p>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}
                              {risks.length > 0 ? (
                                <div className={cardBase}>
                                  <p className={h2}>{translations[lang].cardRiskFlags}</p>
                                  <ul className="space-y-2">
                                    {risks.map((r: unknown, i: number) => {
                                      const o = r as Record<string, unknown>;
                                      return (
                                        <li key={i} className="text-xs">
                                          <span className="font-semibold">
                                            {getRiskTypeLabel(o.type, lang)}
                                          </span>
                                          {" / "}
                                          <span>{getRiskLevelLabel(o.level, lang)}</span>
                                          <p className="mt-0.5">{String(o.reason)}</p>
                                        </li>
                                      );
                                    })}
                                  </ul>
                                </div>
                              ) : null}
                              {Object.keys(pi).length > 0 ? (
                                <div className={cardBase}>
                                  <p className={h2}>{translations[lang].cardPractical}</p>
                                  <dl className="grid gap-1 text-xs">
                                    {Object.entries(pi).map(([k, v]) => (
                                      <div key={k} className="flex gap-2">
                                        <dt className="w-40 shrink-0 opacity-70">
                                          {getPracticalFieldLabel(k, lang)}
                                        </dt>
                                        <dd className="min-w-0 flex-1">{v}</dd>
                                      </div>
                                    ))}
                                  </dl>
                                </div>
                              ) : null}
                              {(Array.isArray(fs.mentionedMenus) &&
                                (fs.mentionedMenus as string[]).length > 0) ||
                              typeof fs.tastePattern === "string" ? (
                                <div className={cardBase}>
                                  <p className={h2}>{translations[lang].cardFoodSignals}</p>
                                  {Array.isArray(fs.mentionedMenus) &&
                                  (fs.mentionedMenus as string[]).length > 0 ? (
                                    <p className="text-xs mb-2">
                                      {(fs.mentionedMenus as string[]).join(", ")}
                                    </p>
                                  ) : null}
                                  {typeof fs.tastePattern === "string" ? (
                                    <p className="text-xs mb-1">{String(fs.tastePattern)}</p>
                                  ) : null}
                                  {typeof fs.portionValuePattern === "string" ? (
                                    <p className="text-xs">{String(fs.portionValuePattern)}</p>
                                  ) : null}
                                </div>
                              ) : null}
                              {lbl === "CAUTION" || lbl === "AVOID" ? (
                                <div className={cardBase}>
                                  <p className={h2}>{translations[lang].cardNearbySafer}</p>
                                  {near.length === 0 ? (
                                    <p className="text-xs opacity-80">
                                      {translations[lang].cardNoAlternatives}
                                    </p>
                                  ) : (
                                    <ul className="space-y-2">
                                      {near.map((a, i) => (
                                        <li
                                          key={i}
                                          className="text-xs rounded-lg border border-slate-200/50 p-2"
                                        >
                                          <p className="font-bold">
                                            {String(a.name ?? "")}{" "}
                                            <span className="text-slate-500 font-normal">
                                              (
                                              {typeof a.visitSafetyScore === "number"
                                                ? (a.visitSafetyScore as number).toFixed(1)
                                                : "?"}{" "}
                                              / 5)
                                            </span>
                                          </p>
                                          <p className="opacity-90">{String(a.oneLine ?? "")}</p>
                                          {typeof a.distanceMeters === "number" ? (
                                            <p className="text-[10px] mt-1 opacity-70">
                                              {translations[lang].approxMetersLabel.replace(
                                                "{n}",
                                                String(Math.round(a.distanceMeters as number)),
                                              )}
                                            </p>
                                          ) : null}
                                        </li>
                                      ))}
                                    </ul>
                                  )}
                                </div>
                              ) : null}
                              {(() => {
                                const conf = kakaoData.confidence as
                                  | Record<string, unknown>
                                  | undefined;
                                if (!conf || typeof conf !== "object") return null;
                                const lvl = conf.level;
                                const reason =
                                  typeof conf.reason === "string" ? conf.reason.trim() : "";
                                const used = conf.usedReviewCount;
                                const lims = Array.isArray(conf.dataLimitations)
                                  ? (conf.dataLimitations as unknown[]).filter(
                                      (x) => typeof x === "string" && String(x).trim(),
                                    )
                                  : [];
                                if (
                                  lvl == null &&
                                  !reason &&
                                  lims.length === 0 &&
                                  used == null
                                )
                                  return null;
                                return (
                                  <div className={cardBase}>
                                    <p className={h2}>{translations[lang].findConfidenceLabel}</p>
                                    {lvl != null ? (
                                      <p className="text-xs font-semibold">
                                        {getConfidenceLevelLabel(lvl, lang)}
                                      </p>
                                    ) : null}
                                    {used != null ? (
                                      <p className="mt-1 text-[11px] text-slate-500">
                                        {translations[lang].findUsedReviewsLabel}: {String(used)}
                                      </p>
                                    ) : null}
                                    {reason ? (
                                      <p className="mt-2 text-xs">
                                        <span className="font-semibold text-slate-600">
                                          {translations[lang].confidenceReasonLabel}:{" "}
                                        </span>
                                        {reason}
                                      </p>
                                    ) : null}
                                    {lims.length > 0 ? (
                                      <div className="mt-2">
                                        <p className="text-[11px] font-bold text-slate-600">
                                          {translations[lang].cardDataLimitationsTitle}
                                        </p>
                                        <ul className="mt-1 list-disc pl-4 text-[11px] space-y-0.5">
                                          {lims.map((s, j) => (
                                            <li key={j}>{String(s)}</li>
                                          ))}
                                        </ul>
                                      </div>
                                    ) : null}
                                  </div>
                                );
                              })()}
                            </div>
                          );
                        })()}
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
                      kakaoData &&
                      !isKakaoDeepFailureStatus(kakaoData) &&
                      String(kakaoData?.kakao_matched_name ?? "").trim() !==
                        "" && (
                        <div
                          className={`rounded-xl border px-3 py-2.5 text-[11px] leading-relaxed ${
                            isCritical
                              ? "border-slate-600 bg-slate-800/50 text-slate-300"
                              : "border-slate-200 bg-slate-50 text-slate-600"
                          }`}
                        >
                          <p
                            className={`text-[10px] font-semibold uppercase tracking-wide ${
                              isCritical ? "text-slate-400" : "text-slate-500"
                            }`}
                          >
                            {translations[lang].kakaoSourceSearchPlace}
                          </p>
                          <p className="mt-1.5 break-words">
                            <span
                              className={
                                isCritical ? "text-slate-400" : "text-slate-500"
                              }
                            >
                              {translations[lang].kakaoSourceReviewOrigin}:
                            </span>{" "}
                            <span
                              className={`font-medium ${isCritical ? "text-slate-100" : "text-slate-800"}`}
                            >
                              {String(kakaoData.kakao_matched_name ?? "").trim()}
                            </span>
                          </p>
                          {String(kakaoData.kakao_matched_address ?? "").trim() !==
                            "" && (
                            <p className="mt-0.5 break-words">
                              <span
                                className={
                                  isCritical ? "text-slate-400" : "text-slate-500"
                                }
                              >
                                {translations[lang].kakaoSourceAddress}:
                              </span>{" "}
                              <span
                                className={`font-medium ${isCritical ? "text-slate-100" : "text-slate-800"}`}
                              >
                                {String(kakaoData.kakao_matched_address ?? "").trim()}
                              </span>
                            </p>
                          )}
                          {kakaoData.sourceStats &&
                            typeof kakaoData.sourceStats === "object" &&
                            !Array.isArray(kakaoData.sourceStats) && (
                              <dl
                                className={`mt-2 space-y-1 border-t pt-2 ${
                                  isCritical ? "border-slate-600" : "border-slate-200"
                                }`}
                              >
                                <div className="flex flex-wrap gap-x-1">
                                  <dt
                                    className={
                                      isCritical ? "text-slate-400" : "text-slate-500"
                                    }
                                  >
                                    {translations[lang].kakaoSourceKakaoRating}:
                                  </dt>
                                  <dd>
                                    {formatKakaoSourceRating(
                                      kakaoData.sourceStats.kakaoAverageRating,
                                      translations[lang].kakaoSourceStatUnavailable,
                                    )}
                                  </dd>
                                </div>
                                <div className="flex flex-wrap gap-x-1">
                                  <dt
                                    className={
                                      isCritical ? "text-slate-400" : "text-slate-500"
                                    }
                                  >
                                    {translations[lang].kakaoSourceKakaoTotalReviews}:
                                  </dt>
                                  <dd>
                                    {formatKakaoSourceNumber(
                                      kakaoData.sourceStats.kakaoTotalReviewCount,
                                    ) ?? translations[lang].kakaoSourceStatUnavailable}
                                  </dd>
                                </div>
                                <div className="flex flex-wrap gap-x-1">
                                  <dt
                                    className={
                                      isCritical ? "text-slate-400" : "text-slate-500"
                                    }
                                  >
                                    {translations[lang].kakaoSourceReviewsAnalyzed}:
                                  </dt>
                                  <dd>
                                    {(() => {
                                      const u = formatKakaoSourceNumber(
                                        kakaoData.sourceStats.usefulReviewCount,
                                      );
                                      const r = formatKakaoSourceNumber(
                                        kakaoData.sourceStats.rawReviewCount,
                                      );
                                      return u !== null && r !== null
                                        ? `${u} / ${r}`
                                        : translations[lang].kakaoSourceStatUnavailable;
                                    })()}
                                  </dd>
                                </div>
                                <div className="flex flex-wrap gap-x-1">
                                  <dt
                                    className={
                                      isCritical ? "text-slate-400" : "text-slate-500"
                                    }
                                  >
                                    {translations[lang].kakaoSourceReviewsUsed}:
                                  </dt>
                                  <dd>
                                    {formatKakaoSourceNumber(
                                      kakaoData.sourceStats.usedReviewCount,
                                    ) ?? translations[lang].kakaoSourceStatUnavailable}
                                  </dd>
                                </div>
                              </dl>
                            )}
                          {kakaoData.sourceStats?.fallbackUsed === true && (
                            <p
                              className={`mt-2 text-[10px] leading-snug ${
                                isCritical
                                  ? "text-amber-200/95"
                                  : "text-amber-800"
                              }`}
                            >
                              ⚠️ {translations[lang].kakaoSourceFallbackUnstable}
                            </p>
                          )}
                        </div>
                      )}

                    {isAdvancedView &&
                      chartDetails &&
                      kakaoData &&
                      advancedAnalysisStatus !== "limited_scan" &&
                      !isKakaoDeepFailureStatus(kakaoData) && (
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
                          if (isKakaoDeepFailureStatus(kakaoData)) {
                            setIsAdvancedView(true);
                            return;
                          }
                          setRealScore(kakaoData.realScore ?? 0);
                          setEventProb(kakaoData.eventProbability ?? 0);
                          const dec = kakaoData?.decision as { oneLine?: string } | undefined;
                          const one =
                            dec && typeof dec.oneLine === "string" && dec.oneLine.trim()
                              ? dec.oneLine.trim()
                              : "";
                          setAiSummary(one || kakaoData.aiSummary || "");
                          setChartDetails(
                            kakaoData.details ?? { taste: 0, value: 0, service: 0, time: 0 },
                          );
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
                        setShowResult(false);
                        setSelectedPlace(null);
                        setHasAdvanced(false);
                        setKakaoData(null);
                        setBasicData(null);
                        setIsAdvancedView(false);
                        setKakaoPollEnabled(false);
                        setPlanB(null);
                        setAdvancedAnalysisStatus(null);
                        setCheckSearchQuery("");
                        setCheckCandidates([]);
                        kakaoTrophyFlagAlertKey = null;
                        setProductFlow("home");
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
              {productFlow === "home" ? (
                <>
                  <header className="mb-10 text-center relative z-10">
                    <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">ZzinView</h1>
                    <p className="mt-3 text-sm text-slate-500 max-w-md mx-auto break-keep">
                      {translations[lang].homeSubtitle}
                    </p>
                  </header>
                  <div className="grid w-full max-w-lg gap-4 relative z-10">
                    <button
                      type="button"
                      onClick={() => setProductFlow("find")}
                      className="rounded-2xl border border-slate-200 bg-white px-5 py-5 text-left shadow-md transition hover:border-slate-400 hover:shadow-lg"
                    >
                      <p className="text-lg font-bold text-slate-900">{translations[lang].homeFindTitle}</p>
                      <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                        {translations[lang].homeFindDesc}
                      </p>
                    </button>
                    <button
                      type="button"
                      onClick={() => setProductFlow("check")}
                      className="rounded-2xl border border-slate-200 bg-white px-5 py-5 text-left shadow-md transition hover:border-slate-400 hover:shadow-lg"
                    >
                      <p className="text-lg font-bold text-slate-900">{translations[lang].homeCheckTitle}</p>
                      <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                        {translations[lang].homeCheckDesc}
                      </p>
                    </button>
                  </div>
                </>
              ) : productFlow === "find" ? (
                <div className="w-full max-w-lg space-y-6">
                  <button
                    type="button"
                    onClick={() => setProductFlow("home")}
                    className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    {lang === "ko" ? "처음" : "Home"}
                  </button>
                  <h2 className="text-2xl font-bold text-slate-900">{translations[lang].findFlowTitle}</h2>
                  <form onSubmit={handleFindVerified} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <label className="block text-sm font-bold text-slate-700">
                      {translations[lang].findAreaLabel}
                      <input
                        value={findArea}
                        onChange={(e) => setFindArea(e.target.value)}
                        placeholder={translations[lang].findAreaPlaceholder}
                        className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="block text-sm font-bold text-slate-700">
                      {translations[lang].findCategoryLabel}
                      <input
                        value={findCategory}
                        onChange={(e) => setFindCategory(e.target.value)}
                        placeholder={translations[lang].findCategoryPlaceholder}
                        className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                      />
                    </label>
                    <div className="space-y-2">
                      <p className="text-sm font-bold text-slate-700">{translations[lang].findPurposeLabel}</p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setFindPurpose("")}
                          className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                            findPurpose === ""
                              ? "border-slate-900 bg-slate-900 text-white"
                              : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300"
                          }`}
                        >
                          {translations[lang].findPurposeAny}
                        </button>
                        {PURPOSE_VALUES.map((pv) => (
                          <button
                            key={pv}
                            type="button"
                            onClick={() => setFindPurpose(findPurpose === pv ? "" : pv)}
                            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                              findPurpose === pv
                                ? "border-slate-900 bg-slate-900 text-white"
                                : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300"
                            }`}
                          >
                            {getPurposeLabel(pv, lang)}
                          </button>
                        ))}
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={findLoading}
                      className="w-full rounded-xl bg-slate-900 py-3 text-sm font-bold text-white disabled:bg-slate-400"
                    >
                      {findLoading ? translations[lang].findLoading : translations[lang].findSubmit}
                    </button>
                  </form>
                  {findEmptyMsg ? (
                    <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                      {findEmptyMsg}
                    </p>
                  ) : null}
                  <ul className="space-y-3">
                    {findResults.map((row, idx) => {
                      const r = row as Record<string, unknown>;
                      const dec = (r.decision as Record<string, unknown>) || {};
                      const risks = Array.isArray(r.topRiskFlags) ? r.topRiskFlags : [];
                      const conf = r.confidence as { level?: unknown } | undefined;
                      return (
                        <li
                          key={`${String(r.name)}-${idx}`}
                          className="rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm"
                        >
                          <p className="font-bold text-slate-900">{String(r.name ?? "")}</p>
                          <p className="text-xs text-slate-500 mt-1">{String(r.address ?? "")}</p>
                          <p className="mt-2 text-xs text-slate-600">
                            {(r.area as { gugun?: string })?.gugun || ""}{" "}
                            {(r.area as { dong?: string })?.dong || ""}
                          </p>
                          <p className="mt-2 font-semibold text-slate-800">
                            {getDecisionDisplayLabel(dec.label, lang)}{" "}
                            <span className="text-slate-500 font-normal">
                              · {translations[lang].findVisitSafetyLabel}{" "}
                              {dec.visitSafetyScore != null ? String(dec.visitSafetyScore) : "—"}
                            </span>
                          </p>
                          <p className="mt-1 text-xs text-slate-700">{String(dec.oneLine ?? "")}</p>
                          <p className="mt-1 text-[11px] text-slate-500">
                            {translations[lang].findConfidenceLabel}:{" "}
                            {getConfidenceLevelLabel(conf?.level, lang)} ·{" "}
                            {translations[lang].findUsedReviewsLabel}{" "}
                            {String(r.usedReviewCount ?? "—")}
                          </p>
                          {risks.length > 0 ? (
                            <ul className="mt-2 text-[11px] text-amber-900 space-y-1">
                              {(risks as { type?: string; level?: string }[]).map((x, i) => (
                                <li key={i}>
                                  {getRiskTypeLabel(x.type, lang)} ({getRiskLevelLabel(x.level, lang)})
                                </li>
                              ))}
                            </ul>
                          ) : null}
                          {r.foreignerAccessHint ? (
                            <p className="mt-2 text-[11px] text-slate-600">
                              {getPracticalFieldLabel("foreignerAccess", lang)}:{" "}
                              {String(r.foreignerAccessHint)}
                            </p>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : (
                <div className="w-full max-w-lg space-y-6">
                  <button
                    type="button"
                    onClick={() => setProductFlow("home")}
                    className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    {lang === "ko" ? "처음" : "Home"}
                  </button>
                  <h2 className="text-2xl font-bold text-slate-900">{translations[lang].checkFlowTitle}</h2>
                  <p className="text-sm text-slate-600">{translations[lang].checkCandidateHint}</p>
                  <form
                    onSubmit={handleCheckCandidatesSubmit}
                    className="flex flex-col gap-3 sm:flex-row sm:items-end"
                  >
                    <label className="flex-1 text-sm font-bold text-slate-700">
                      {translations[lang].checkRestaurantNameLabel}
                      <input
                        value={checkSearchQuery}
                        onChange={(e) => setCheckSearchQuery(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                        placeholder={translations[lang].checkNamePlaceholder}
                      />
                    </label>
                    <button
                      type="submit"
                      disabled={checkSearching || !checkSearchQuery.trim()}
                      className="rounded-xl bg-slate-900 px-5 py-2 text-sm font-bold text-white disabled:bg-slate-400"
                    >
                      {checkSearching
                        ? translations[lang].searching
                        : translations[lang].checkFindCandidatesButton}
                    </button>
                  </form>
                  <ul className="space-y-2">
                    {checkCandidates.map((c) => (
                      <li key={`${c.name}-${c.address}`}>
                        <button
                          type="button"
                          onClick={() => {
                            handleAnalyzePlace({ name: c.name, address: c.address });
                          }}
                          className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-800 transition hover:bg-slate-100"
                        >
                          <p className="font-medium text-slate-900">{c.name}</p>
                          <p className="mt-0.5 text-xs text-slate-500">{c.address}</p>
                          {c.rating != null ? (
                            <p className="mt-1 text-[11px] text-slate-500">
                              {translations[lang].candidateGoogleRatingLine} ★{c.rating} (
                              {c.user_ratings_total ?? "—"} {translations[lang].candidateReviewsWord})
                            </p>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
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