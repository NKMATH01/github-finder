"use client";

import type { SearchStatus } from "@/lib/types";
import { Progress } from "@/components/ui/progress";

const STEP_LABELS: Record<number, string> = {
  0: "준비 중",
  1: "브리프 분석",
  2: "키워드 확장",
  3: "GitHub 검색",
  4: "상세 정보 조회",
  5: "AI 딥 리딩",
  6: "3종 분류",
  7: "결과 정리",
};

interface SearchProgressProps {
  status: SearchStatus;
}

export function SearchProgress({ status }: SearchProgressProps) {
  const currentStep = status.step ?? 0;

  return (
    <div className="w-full max-w-md space-y-8 text-center">
      {/* 스피너 */}
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/10 to-violet-500/10">
        <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-slate-200 border-t-blue-600" />
      </div>

      {/* 메시지 */}
      <div>
        <h2 className="text-xl font-semibold text-slate-900">
          GitHub에서 최적의 코드를 찾고 있습니다
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          {status.message || "브리프를 분석하고 키워드를 확장하는 중..."}
        </p>
      </div>

      {/* 프로그레스 바 */}
      <div className="space-y-2">
        <Progress value={status.progress ?? 10} className="h-2" />
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>
            Step {currentStep}/7 — {STEP_LABELS[currentStep] || "진행 중"}
          </span>
          <span>{status.progress}%</span>
        </div>
      </div>

      {/* 단계 인디케이터 */}
      <div className="flex justify-center gap-1.5">
        {[1, 2, 3, 4, 5, 6, 7].map((step) => (
          <div
            key={step}
            className={`h-1.5 w-6 rounded-full transition-colors ${
              step < currentStep
                ? "bg-blue-500"
                : step === currentStep
                ? "bg-blue-400 animate-pulse"
                : "bg-slate-200"
            }`}
            title={STEP_LABELS[step]}
          />
        ))}
      </div>

      {/* 경고 메시지 */}
      {status.warnings && status.warnings.length > 0 && (
        <div className="space-y-1.5">
          {status.warnings.map((warn, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200/60 px-3 py-2 text-xs text-amber-700"
            >
              <svg className="h-3.5 w-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              {warn}
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-slate-400">SSE 실시간 연결 중</p>
    </div>
  );
}
