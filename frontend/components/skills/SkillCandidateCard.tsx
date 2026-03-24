"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { SkillCandidate } from "@/hooks/useSkillSearch";

const RANK_CONFIG: Record<number, { icon: string; gradient: string }> = {
  1: { icon: "1", gradient: "from-amber-500 to-orange-500" },
  2: { icon: "2", gradient: "from-slate-400 to-slate-500" },
  3: { icon: "3", gradient: "from-orange-400 to-amber-600" },
};

const CATEGORY_LABELS: Record<string, { label: string; desc: string; color: string }> = {
  "완성도최고": { label: "완성도 최고", desc: "믿고 쓸 수 있는 스킬", color: "text-blue-600 bg-blue-50 border-blue-200" },
  "바로적용": { label: "바로 적용", desc: "지금 바로 쓸 수 있는 스킬", color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  "가장강력": { label: "가장 강력", desc: "제대로 쓰면 최강", color: "text-violet-600 bg-violet-50 border-violet-200" },
};

interface SkillCandidateCardProps {
  candidate: SkillCandidate;
  rank: number;
}

export function SkillCandidateCard({ candidate, rank }: SkillCandidateCardProps) {
  const [showMd, setShowMd] = useState(false);
  const [showInstall, setShowInstall] = useState(false);
  const [copied, setCopied] = useState(false);

  const rankStyle = RANK_CONFIG[rank] ?? RANK_CONFIG[3];
  const cat = CATEGORY_LABELS[candidate.category] ?? {
    label: candidate.category, desc: "", color: "text-slate-600 bg-slate-50 border-slate-200",
  };

  const scoreColor = candidate.total_score >= 80 ? "text-emerald-600" : candidate.total_score >= 60 ? "text-blue-600" : "text-amber-600";

  const handleCopySkillMd = async () => {
    try {
      await navigator.clipboard.writeText(candidate.skill_md_preview || "SKILL.md 내용을 불러올 수 없습니다.");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  const scoreDetail = candidate.score_detail;
  const scoreItems = [
    { label: "기능 매칭", value: scoreDetail.feature_match, max: 30 },
    { label: "품질", value: scoreDetail.quality, max: 25 },
    { label: "호환성", value: scoreDetail.compatibility, max: 20 },
    { label: "신뢰도", value: scoreDetail.community_trust, max: 15 },
    { label: "설치", value: scoreDetail.install_ease, max: 10 },
  ];

  return (
    <div className="group relative flex flex-col rounded-2xl border border-slate-200/60 bg-white shadow-sm hover:shadow-lg hover:border-slate-300/60 transition-all duration-300 overflow-hidden">
      {/* 상단 그라데이션 바 */}
      <div className={`h-1 bg-gradient-to-r ${rankStyle.gradient}`} />

      <div className="flex flex-col flex-1 p-5">
        {/* 헤더 */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`inline-flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-r ${rankStyle.gradient} text-white text-xs font-bold`}>
                {rankStyle.icon}
              </span>
              <span className={`inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${cat.color}`}>
                {cat.label}
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 truncate">
              {candidate.skill_name}
            </h3>
            <p className="text-xs text-slate-400 truncate">{candidate.author}</p>
          </div>
          <div className="text-right shrink-0 ml-3">
            <p className={`text-2xl font-bold ${scoreColor}`}>{candidate.total_score}</p>
            <p className="text-[10px] text-slate-400 -mt-0.5">/100</p>
          </div>
        </div>

        {/* 메타 */}
        <div className="flex items-center gap-3 mb-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">GitHub {candidate.stars.toLocaleString()}</span>
        </div>

        {/* 설명 */}
        {candidate.category_reason && (
          <p className="text-xs text-slate-500 italic mb-3">"{candidate.category_reason}"</p>
        )}

        {/* 5축 스코어 바 */}
        <div className="mb-3 space-y-1.5 rounded-lg bg-slate-50 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">5축 스코어</p>
          {scoreItems.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span className="text-[10px] text-slate-500 w-14 shrink-0">{item.label}</span>
              <div className="flex-1 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all"
                  style={{ width: `${(item.value / item.max) * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-400 w-8 text-right">{item.value}/{item.max}</span>
            </div>
          ))}
        </div>

        {/* 장단점 */}
        <div className="flex-1 space-y-1.5 mb-3">
          {candidate.pros.slice(0, 2).map((pro, i) => (
            <p key={`p${i}`} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-emerald-500 shrink-0">+</span>
              <span className="line-clamp-2">{pro}</span>
            </p>
          ))}
          {candidate.cons.slice(0, 2).map((con, i) => (
            <p key={`c${i}`} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-red-400 shrink-0">-</span>
              <span className="line-clamp-2">{con}</span>
            </p>
          ))}
        </div>

        {/* 주의사항 */}
        {candidate.warnings.length > 0 && (
          <div className="mb-3 space-y-1">
            {candidate.warnings.slice(0, 2).map((w, i) => (
              <div key={i} className="flex items-center gap-1.5 rounded-lg bg-amber-50 border border-amber-200/60 px-2.5 py-1.5 text-[11px] text-amber-700">
                <span className="shrink-0">!</span> {w}
              </div>
            ))}
          </div>
        )}

        {/* SKILL.md 미리보기 (접기/펼치기) */}
        {candidate.skill_md_preview && (
          <div className="mb-3">
            <button
              onClick={() => setShowMd(!showMd)}
              className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-violet-600 transition-colors"
            >
              <svg className={`h-3 w-3 transition-transform ${showMd ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
              SKILL.md 미리보기
            </button>
            {showMd && (
              <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] text-slate-600 font-mono whitespace-pre-wrap border border-slate-100">
                {candidate.skill_md_preview}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* 버튼 영역 */}
      <div className="border-t border-slate-100 p-4 space-y-2 bg-slate-50/50">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 rounded-xl text-xs h-9 border-slate-200 hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700"
            onClick={handleCopySkillMd}
          >
            {copied ? "복사됨!" : "SKILL.md 복사"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 rounded-xl text-xs h-9 border-slate-200 hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700"
            onClick={() => setShowInstall(!showInstall)}
          >
            설치 가이드
          </Button>
        </div>

        {showInstall && (
          <div className="rounded-xl bg-slate-900 p-3 text-xs text-slate-300 font-mono space-y-1">
            <p className="text-violet-400"># 프로젝트에 설치</p>
            <p>mkdir -p .claude/skills/{candidate.skill_name}</p>
            <p className="text-slate-500"># GitHub에서 SKILL.md를 다운로드하세요</p>
            <p className="text-violet-400 mt-2"># 또는 개인 설치</p>
            <p>mkdir -p ~/.claude/skills/{candidate.skill_name}</p>
          </div>
        )}

        <a
          href={candidate.github_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full rounded-xl py-1.5 text-center text-[11px] text-slate-400 hover:text-violet-600 hover:bg-violet-50 transition-colors"
        >
          GitHub에서 보기 &rarr;
        </a>
      </div>
    </div>
  );
}
