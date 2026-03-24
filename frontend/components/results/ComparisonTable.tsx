"use client";

import type { Candidate } from "@/lib/types";

const RANK_ICONS: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

interface ComparisonTableProps {
  candidates: Candidate[];
}

export function ComparisonTable({ candidates }: ComparisonTableProps) {
  if (candidates.length === 0) return null;

  const rows: { label: string; icon: string; getValue: (c: Candidate) => string; highlight?: (c: Candidate) => string }[] = [
    { label: "성격", icon: "🏷", getValue: (c) => c.category },
    { label: "총점", icon: "📊", getValue: (c) => `${c.total_score}`, highlight: (c) => c.total_score >= 80 ? "text-emerald-600 font-bold" : c.total_score >= 60 ? "text-blue-600 font-semibold" : "text-amber-600" },
    { label: "Stars", icon: "⭐", getValue: (c) => c.stars.toLocaleString() },
    { label: "기능 일치", icon: "🎯", getValue: (c) => `${c.score_detail.feature_match}/25` },
    { label: "실행 가능", icon: "▶", getValue: (c) => `${c.score_detail.runnability}/20` },
    { label: "설치 난이도", icon: "📦", getValue: (c) => `${c.score_detail.install_ease}/10` },
    { label: "스택 호환", icon: "🔧", getValue: (c) => `${c.score_detail.stack_compatibility}/5` },
    { label: "예상 크기", icon: "💾", getValue: (c) => c.estimated_size_mb ? `~${c.estimated_size_mb}MB` : "-" },
  ];

  return (
    <div className="rounded-2xl border border-slate-200/60 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50/50 px-5 py-3">
        <p className="text-sm font-semibold text-slate-700">📊 한눈에 비교</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="py-3 px-5 text-left text-xs font-medium text-slate-400 uppercase tracking-wider w-32">항목</th>
              {candidates.map((c) => (
                <th key={c.id} className="py-3 px-4 text-center text-sm font-semibold text-slate-700">
                  {RANK_ICONS[c.rank]} {c.repo_name.split("/").pop()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.label} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/30"}>
                <td className="py-2.5 px-5 text-xs text-slate-500">
                  <span className="mr-1.5">{row.icon}</span>{row.label}
                </td>
                {candidates.map((c) => (
                  <td key={c.id} className={`py-2.5 px-4 text-center text-xs ${row.highlight?.(c) ?? "text-slate-700"}`}>
                    {row.getValue(c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
