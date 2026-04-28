"use client";

export type PlanBPayload = {
  tags: string[];
  /** Romanized sub-tags (Samgyeopsal, K-BBQ, …) for foreigner-friendly UI */
  romanized_food_for_ui?: string[];
  /** 신뢰도 방어: 근거 없으면 null — Plan B UI 비노출 */
  alternative_query: {
    suggest_message: string | null;
    target_category: string;
    target_category_ko?: string;
    primary_romanized_food?: string;
    avoid: string;
    query_hint?: string;
    worry_id?: string;
  } | null;
};

type Lang = "ko" | "en";

type Labels = {
  badge: string;
  footnote: string;
  comingSoon: string;
};

type Props = {
  lang: Lang;
  data: PlanBPayload | null;
  isCritical: boolean;
  labels: Labels;
};

export default function PlanBSection({ lang, data, isCritical, labels }: Props) {
  const aq = data?.alternative_query;
  const sm = aq?.suggest_message;
  if (
    aq == null ||
    sm == null ||
    typeof sm !== "string" ||
    sm.trim() === ""
  ) {
    return null;
  }

  const cat = (aq.target_category || "맛집").trim();
  const catKo = (aq.target_category_ko || "").trim();
  const r0 = (aq.primary_romanized_food || "").trim();
  const cta =
    lang === "en"
      ? r0
        ? `See verified ${r0} · ${cat} nearby`
        : `See verified ${cat} picks nearby`
      : r0 && catKo
        ? `근처 검증된 ${r0} · ${catKo} 맛집 보기`
        : `근처 검증된 ${catKo || cat} 맛집 보기`;

  return (
    <section
      className={`mt-8 rounded-2xl border p-5 sm:p-6 shadow-md transition-colors ${
        isCritical
          ? "border-indigo-800/60 bg-gradient-to-br from-indigo-950/80 to-slate-900 text-indigo-50"
          : "border-indigo-200 bg-gradient-to-br from-indigo-50 via-white to-violet-50 text-slate-900"
      }`}
      aria-labelledby="plan-b-heading"
    >
      <p
        className={`text-[11px] font-black uppercase tracking-[0.2em] ${
          isCritical ? "text-indigo-300/90" : "text-indigo-600/80"
        }`}
      >
        {labels.badge}
      </p>
      <h3
        id="plan-b-heading"
        className={`mt-3 text-lg sm:text-xl font-black leading-snug ${
          isCritical ? "text-white" : "text-slate-900"
        }`}
      >
        {sm}
      </h3>

      {(data?.romanized_food_for_ui && data.romanized_food_for_ui.length > 0) ||
      (data?.tags && data.tags.length > 0) ? (
        <div className="mt-4 flex flex-wrap gap-2" aria-label="food & situation tags">
          {(data.romanized_food_for_ui && data.romanized_food_for_ui.length > 0
            ? data.romanized_food_for_ui
            : data.tags
          ).map((t) => (
            <span
              key={t}
              className={`rounded-full px-3 py-1 text-[11px] font-bold border ${
                isCritical
                  ? "border-indigo-500/40 bg-indigo-950/50 text-indigo-100"
                  : "border-indigo-100 bg-white/90 text-indigo-900 shadow-sm"
              }`}
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => alert(labels.comingSoon)}
        className={`mt-5 w-full rounded-xl px-4 py-3.5 text-sm font-black shadow-lg transition hover:opacity-95 active:scale-[0.99] ${
          isCritical
            ? "bg-indigo-500 text-white hover:bg-indigo-400"
            : "bg-indigo-600 text-white hover:bg-indigo-700"
        }`}
      >
        {cta}
      </button>

      <p
        className={`mt-3 text-center text-[10px] leading-relaxed ${
          isCritical ? "text-indigo-200/80" : "text-slate-500"
        }`}
      >
        {labels.footnote}
      </p>
    </section>
  );
}
