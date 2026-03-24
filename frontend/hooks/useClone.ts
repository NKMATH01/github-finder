"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { CloneStatus, ClonePreview } from "@/lib/types";

export function useClone() {
  const [cloneId, setCloneId] = useState<string | null>(null);
  const [isCloning, setIsCloning] = useState(false);
  const [cloneError, setCloneError] = useState<string | null>(null);

  // 클론+분석 상태 폴링 (완료 전까지 2초 간격)
  const { data: cloneStatus } = useSWR<CloneStatus>(
    cloneId ? `/clone/${cloneId}/status` : null,
    fetcher,
    {
      refreshInterval:
        cloneId ? 2000 : 0,
      revalidateOnFocus: false,
    }
  );

  // 완료/실패 시 폴링 중지
  const isComplete =
    cloneStatus?.status === "completed" || cloneStatus?.status === "failed";

  const startClone = useCallback(async (candidateId: string) => {
    setIsCloning(true);
    setCloneError(null);
    try {
      const res = await api.startClone(candidateId);
      setCloneId(res.clone_id);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "error" in err
          ? (err as { error: { message: string } }).error.message
          : "클론 요청에 실패했습니다.";
      setCloneError(message);
    } finally {
      setIsCloning(false);
    }
  }, []);

  const getPreview = useCallback(async (candidateId: string) => {
    return api.getClonePreview(candidateId);
  }, []);

  const reset = useCallback(() => {
    setCloneId(null);
    setCloneError(null);
  }, []);

  return {
    startClone,
    getPreview,
    isCloning,
    cloneError,
    cloneId,
    cloneStatus,
    isComplete,
    reset,
  };
}
