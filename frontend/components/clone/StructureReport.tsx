"use client";

import type { SafeModule, RiskyModule, FailModule } from "@/lib/types";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface StructureReportProps {
  safe: SafeModule[];
  risky: RiskyModule[];
  fail: FailModule[];
  summary?: string;
}

export function StructureReport({ safe, risky, fail, summary }: StructureReportProps) {
  const hasContent = safe.length > 0 || risky.length > 0 || fail.length > 0;

  if (!hasContent) {
    return (
      <div className="rounded-lg border bg-white p-4 text-center text-sm text-gray-400">
        구조 분석 결과가 없습니다.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white p-5 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-800">구조 분석 리포트</p>
        <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-[10px] text-yellow-700">
          LLM 분석 기반
        </span>
      </div>

      {summary && (
        <p className="text-sm text-gray-600">{summary}</p>
      )}

      {/* ✅ Safe */}
      {safe.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-green-700">
            ✅ 바로 통합 가능 ({safe.length}개)
          </p>
          {safe.map((m, i) => (
            <div key={i} className="ml-2 rounded bg-green-50 px-3 py-2 text-xs">
              <code className="font-semibold text-green-800">{m.file_path}</code>
              {m.target_path && (
                <span className="text-green-600"> → {m.target_path}</span>
              )}
              <p className="mt-0.5 text-green-700">{m.action}</p>
              <p className="text-green-600 opacity-80">{m.reason}</p>
            </div>
          ))}
        </div>
      )}

      {/* ⚠️ Risky */}
      {risky.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-yellow-700">
            ⚠️ 의존성 충돌 위험 ({risky.length}개)
          </p>
          {risky.map((m, i) => (
            <div key={i} className="ml-2 rounded bg-yellow-50 px-3 py-2 text-xs">
              <code className="font-semibold text-yellow-800">{m.file_path}</code>
              {m.package_name && (
                <span className="text-yellow-600"> ({m.package_name})</span>
              )}
              <p className="mt-0.5 text-yellow-700">문제: {m.issue}</p>
              <p className="text-yellow-600">해결: {m.solution}</p>
              <span className={`inline-block mt-1 rounded px-1.5 py-0.5 text-[10px] ${
                m.severity === "high" ? "bg-red-100 text-red-700" :
                m.severity === "medium" ? "bg-yellow-100 text-yellow-700" :
                "bg-gray-100 text-gray-600"
              }`}>
                {m.severity}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ❌ Fail */}
      {fail.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-red-700">
            ❌ 환경 제약으로 실패 가능 ({fail.length}개)
          </p>
          {fail.map((m, i) => (
            <div key={i} className="ml-2 rounded bg-red-50 px-3 py-2 text-xs">
              <code className="font-semibold text-red-800">{m.file_path}</code>
              <p className="mt-0.5 text-red-700">문제: {m.issue}</p>
              {m.environment_constraint && (
                <p className="text-red-600">제약: {m.environment_constraint}</p>
              )}
              <p className="text-red-600">대안: {m.alternative}</p>
            </div>
          ))}
        </div>
      )}

      <Alert>
        <AlertDescription className="text-xs text-gray-500">
          ⚠️ 이 리포트는 LLM 분석 기반이며, 실제 실행 전에는 보장할 수 없습니다.
          테스트 후 진행하세요.
        </AlertDescription>
      </Alert>
    </div>
  );
}
