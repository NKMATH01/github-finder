"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

const ERROR_MESSAGES: Record<string, string> = {
  GITHUB_RATE_LIMIT: "GitHub API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
  LLM_TIMEOUT: "AI 분석 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
  LLM_API_ERROR: "AI 서비스에 문제가 발생했습니다.",
  CLONE_FAILED: "레포 클론에 실패했습니다.",
  CLONE_TIMEOUT: "클론 시간이 초과되었습니다.",
  CLONE_SIZE_EXCEEDED: "레포 크기가 상한을 초과합니다.",
  SUPABASE_ERROR: "데이터베이스 연결에 문제가 발생했습니다.",
  NO_CANDIDATES: "조건에 맞는 후보를 찾지 못했습니다. 키워드를 수정해보세요.",
  GIT_NOT_INSTALLED: "git이 설치되지 않았습니다.",
};

interface ErrorDisplayProps {
  error: { error: { code: string; message: string; retry_after?: number } } | string | null;
  onRetry?: () => void;
}

export function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
  if (!error) return null;

  let message: string;
  let retryAfter: number | undefined;

  if (typeof error === "string") {
    message = error;
  } else {
    const code = error.error?.code ?? "";
    message = error.error?.message ?? ERROR_MESSAGES[code] ?? "오류가 발생했습니다.";
    retryAfter = error.error?.retry_after;
  }

  return (
    <Alert variant="destructive">
      <AlertDescription className="flex items-center justify-between">
        <span>{message}</span>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry} className="ml-4">
            다시 시도
          </Button>
        )}
      </AlertDescription>
      {retryAfter && (
        <p className="mt-1 text-xs opacity-70">
          {retryAfter}초 후 다시 시도할 수 있습니다.
        </p>
      )}
    </Alert>
  );
}
