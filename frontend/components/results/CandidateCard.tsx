"use client";

import type { Candidate } from "@/lib/types";
import { Button } from "@/components/ui/button";

const RANK_CONFIG: Record<number, { icon: string; gradient: string; ring: string }> = {
  1: { icon: "🥇", gradient: "from-amber-500 to-orange-500", ring: "ring-amber-200" },
  2: { icon: "🥈", gradient: "from-slate-400 to-slate-500", ring: "ring-slate-200" },
  3: { icon: "🥉", gradient: "from-orange-400 to-amber-600", ring: "ring-orange-200" },
};

const CATEGORY_LABELS: Record<string, { label: string; desc: string; color: string }> = {
  "완성도최고": { label: "완성도 최고", desc: "안정적으로 쓰고 싶다면", color: "text-blue-600 bg-blue-50 border-blue-200" },
  "통합용이": { label: "통합 용이", desc: "빨리 붙이고 싶다면", color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  "고정밀": { label: "고정밀", desc: "정확도가 중요하다면", color: "text-violet-600 bg-violet-50 border-violet-200" },
  "난이도하": { label: "난이도 하", desc: "가장 쉬운 선택", color: "text-green-600 bg-green-50 border-green-200" },
  "난이도중": { label: "난이도 중", desc: "균형 잡힌 선택", color: "text-yellow-600 bg-yellow-50 border-yellow-200" },
  "난이도상": { label: "난이도 상", desc: "강력하지만 복잡한", color: "text-red-600 bg-red-50 border-red-200" },
};

interface CandidateCardProps {
  candidate: Candidate;
  onClone: (c: Candidate) => void;
  onCopyPrompt: (c: Candidate) => void;
  onToggleFavorite: (c: Candidate) => void;
  isFavorite: boolean;
  onShowDetail: (c: Candidate) => void;
}

export function CandidateCard({
  candidate, onClone, onCopyPrompt, onToggleFavorite, isFavorite, onShowDetail,
}: CandidateCardProps) {
  const rank = RANK_CONFIG[candidate.rank] ?? RANK_CONFIG[3];
  const cat = CATEGORY_LABELS[candidate.category] ?? { label: candidate.category, desc: "", color: "text-slate-600 bg-slate-50 border-slate-200" };

  const scoreColor = candidate.total_score >= 80 ? "text-emerald-600" : candidate.total_score >= 60 ? "text-blue-600" : "text-amber-600";

  return (
    <div className={`group relative flex flex-col rounded-2xl border border-slate-200/60 bg-white shadow-sm hover:shadow-lg hover:border-slate-300/60 transition-all duration-300 overflow-hidden`}>
      {/* 상단 그라데이션 바 */}
      <div className={`h-1 bg-gradient-to-r ${rank.gradient}`} />

      <div className="flex flex-col flex-1 p-5">
        {/* 헤더 */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{rank.icon}</span>
              <span className={`inline-flex items-center rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${cat.color}`}>
                {cat.label}
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 truncate">
              {candidate.repo_name.split("/").pop()}
            </h3>
            <p className="text-xs text-slate-400 truncate">{candidate.repo_name}</p>
          </div>
          <div className="text-right shrink-0 ml-3">
            <p className={`text-2xl font-bold ${scoreColor}`}>{candidate.total_score}</p>
            <p className="text-[10px] text-slate-400 -mt-0.5">/100점</p>
          </div>
        </div>

        {/* 메타 */}
        <div className="flex items-center gap-3 mb-4 text-xs text-slate-400">
          <span className="flex items-center gap-1">⭐ {candidate.stars.toLocaleString()}</span>
          {candidate.estimated_size_mb && (
            <span>📦 ~{candidate.estimated_size_mb}MB</span>
          )}
        </div>

        {/* 핵심 파일 */}
        {candidate.key_files.length > 0 && (
          <div className="mb-3 rounded-lg bg-slate-50 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5">핵심 파일</p>
            {candidate.key_files.slice(0, 3).map((kf, i) => (
              <p key={i} className="text-xs text-slate-600 truncate">
                <code className="text-blue-600">{kf.path}</code>
              </p>
            ))}
          </div>
        )}

        {/* 장단점 */}
        <div className="flex-1 space-y-2 mb-4">
          {candidate.pros.slice(0, 2).map((pro, i) => (
            <p key={`p${i}`} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-emerald-500 shrink-0">✓</span>
              <span className="line-clamp-2">{pro}</span>
            </p>
          ))}
          {candidate.cons.slice(0, 2).map((con, i) => (
            <p key={`c${i}`} className="text-xs text-slate-600 flex gap-1.5">
              <span className="text-red-400 shrink-0">✗</span>
              <span className="line-clamp-2">{con}</span>
            </p>
          ))}
        </div>

        {/* 카테고리 설명 */}
        {cat.desc && (
          <p className="text-[11px] text-slate-400 italic mb-4">
            "{cat.desc}"
          </p>
        )}
      </div>

      {/* 버튼 영역 */}
      <div className="border-t border-slate-100 p-4 space-y-2 bg-slate-50/50">
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 rounded-xl text-xs h-9 border-slate-200 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
            onClick={() => onCopyPrompt(candidate)}
          >
            💡 프롬프트
          </Button>
          <Button
            size="sm"
            className="flex-1 rounded-xl text-xs h-9 bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-sm hover:shadow-md hover:brightness-110"
            onClick={() => onClone(candidate)}
          >
            📦 가져오기
          </Button>
        </div>
        <div className="flex gap-2">
          <button
            className="flex-1 rounded-xl py-1.5 text-[11px] text-slate-400 hover:text-amber-500 hover:bg-amber-50 transition-colors"
            onClick={() => onToggleFavorite(candidate)}
          >
            {isFavorite ? "⭐ 저장됨" : "☆ 즐겨찾기"}
          </button>
          <button
            className="flex-1 rounded-xl py-1.5 text-[11px] text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
            onClick={() => onShowDetail(candidate)}
          >
            상세 보기 →
          </button>
        </div>
      </div>
    </div>
  );
}
