"use client";

import type { Candidate } from "@/lib/types";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";

interface DetailModalProps {
  candidate: Candidate | null;
  open: boolean;
  onClose: () => void;
}

const SCORE_AXES = [
  { key: "feature_match" as const, label: "기능 일치도", max: 25 },
  { key: "runnability" as const, label: "실행 가능성", max: 20 },
  { key: "maintenance" as const, label: "유지보수", max: 15 },
  { key: "issue_resolution" as const, label: "이슈 해결", max: 15 },
  { key: "install_ease" as const, label: "설치 난이도", max: 10 },
  { key: "documentation" as const, label: "문서 품질", max: 10 },
  { key: "stack_compatibility" as const, label: "스택 호환", max: 5 },
];

export function DetailModal({ candidate, open, onClose }: DetailModalProps) {
  if (!candidate) return null;

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-h-[85vh] overflow-y-auto max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>{candidate.repo_name}</span>
            <Badge variant="secondary" className="text-xs">
              {candidate.category}
            </Badge>
          </DialogTitle>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>⭐ {candidate.stars.toLocaleString()}</span>
            <span>총점: {candidate.total_score}/100</span>
            <a
              href={candidate.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              GitHub에서 보기 ↗
            </a>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* 7축 점수 차트 */}
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">7축 평가</p>
            <div className="space-y-2">
              {SCORE_AXES.map(({ key, label, max }) => {
                const score = candidate.score_detail[key] ?? 0;
                const pct = (score / max) * 100;
                return (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <span className="w-20 text-gray-600">{label}</span>
                    <Progress value={pct} className="flex-1 h-2" />
                    <span className="w-10 text-right text-gray-500">
                      {score}/{max}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <Separator />

          {/* 핵심 파일 */}
          {candidate.key_files.length > 0 && (
            <div>
              <p className="mb-1 text-sm font-medium text-gray-700">📁 핵심 파일</p>
              {candidate.key_files.map((kf, i) => (
                <div key={i} className="ml-2 text-xs text-gray-600 py-0.5">
                  <code className="text-blue-700">{kf.path}</code>
                  <span className="mx-1 text-gray-300">—</span>
                  <span>{kf.role}</span>
                  <Badge variant="outline" className="ml-1 text-[10px] py-0">
                    {kf.importance}
                  </Badge>
                </div>
              ))}
            </div>
          )}

          <Separator />

          {/* 장점 */}
          <div>
            <p className="mb-1 text-sm font-medium text-green-700">✅ 장점</p>
            {candidate.pros.map((pro, i) => (
              <p key={i} className="ml-2 text-xs text-gray-600 py-0.5">{i + 1}. {pro}</p>
            ))}
          </div>

          {/* 단점 */}
          <div>
            <p className="mb-1 text-sm font-medium text-red-700">❌ 단점 + 실패 시나리오</p>
            {candidate.cons.map((con, i) => (
              <p key={i} className="ml-2 text-xs text-gray-600 py-0.5">{i + 1}. {con}</p>
            ))}
          </div>

          {/* 실패 시나리오 */}
          {candidate.failure_scenarios.length > 0 && (
            <div>
              <p className="mb-1 text-sm font-medium text-orange-700">⚠️ 구체적 실패 시나리오</p>
              {candidate.failure_scenarios.map((s, i) => (
                <p key={i} className="ml-2 text-xs text-gray-600 py-0.5">• {s}</p>
              ))}
            </div>
          )}

          {/* 클론 사전 정보 */}
          {candidate.estimated_size_mb && (
            <>
              <Separator />
              <div className="text-xs text-gray-500 space-y-0.5">
                <p>📦 예상 크기: ~{candidate.estimated_size_mb}MB</p>
                <p>⏱ 예상 시간: ~{candidate.estimated_clone_seconds ?? "?"}초</p>
                {candidate.known_install_issues.map((issue, i) => (
                  <p key={i}>⚠️ {issue}</p>
                ))}
                {candidate.stack_conflicts.map((conflict, i) => (
                  <p key={i}>🔧 {conflict}</p>
                ))}
              </div>
            </>
          )}

          <div className="rounded bg-yellow-50 px-3 py-2 text-[10px] text-yellow-700">
            신뢰도: LLM 분석 기반 (실행 미검증)
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
