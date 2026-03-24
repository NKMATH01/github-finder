"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { BriefInput, SearchResults, SearchStatus, SSEEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export function useSearch() {
  const [searchId, setSearchId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sseStatus, setSseStatus] = useState<SearchStatus | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // SSE 연결
  useEffect(() => {
    if (!searchId) return;

    const es = new EventSource(`${API_BASE}/search/${searchId}/stream`);
    eventSourceRef.current = es;
    setSseConnected(true);

    es.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data);
        if (data.status === "heartbeat") return;

        setSseStatus({
          status: data.status === "running" ? "processing" : data.status,
          progress: data.progress,
          message: data.message,
          step: data.step,
          warnings: data.warnings,
        });

        // 종료 상태이면 SSE 닫기
        if (["completed", "failed", "no_results"].includes(data.status)) {
          es.close();
          setSseConnected(false);
        }
      } catch {
        // JSON 파싱 오류는 무시
      }
    };

    es.onerror = () => {
      // EventSource는 자동 재연결, 최종 실패 시에만 fallback
      setSseConnected(false);
    };

    return () => {
      es.close();
      setSseConnected(false);
    };
  }, [searchId]);

  // SSE 실패 시 폴링 fallback (2초 간격)
  const shouldPoll = searchId && !sseConnected && sseStatus?.status !== "completed" && sseStatus?.status !== "failed";
  const { data: polledStatus } = useSWR<SearchStatus>(
    shouldPoll ? `/search/${searchId}/status` : null,
    fetcher,
    {
      refreshInterval: 2000,
      revalidateOnFocus: false,
      errorRetryCount: 5,
      errorRetryInterval: 2000,
      shouldRetryOnError: true,
      onError: () => {},
    }
  );

  // SSE 우선, 폴링 fallback
  const status = sseStatus || polledStatus || null;
  const isCompleted = status?.status === "completed";
  const isFailed = status?.status === "failed" || status?.status === "no_results";

  // completed일 때만 결과 페칭
  const { data: results } = useSWR<SearchResults>(
    searchId && isCompleted ? `/search/${searchId}/results` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      errorRetryCount: 3,
      onError: () => {},
    }
  );

  const pipelineError = isFailed ? (status?.message || "검색에 실패했습니다.") : null;

  const submitBrief = useCallback(async (brief: BriefInput) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSseStatus(null);
    try {
      const res = await api.createSearch(brief);
      setSearchId(res.search_id);
    } catch (err: unknown) {
      let message = "검색 요청에 실패했습니다.";
      if (err instanceof Error) {
        message = err.message;
      } else if (err && typeof err === "object" && "error" in err) {
        message = (err as { error: { message: string } }).error.message;
      }
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const reset = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setSearchId(null);
    setSubmitError(null);
    setSseStatus(null);
    setSseConnected(false);
  }, []);

  return {
    submitBrief,
    isSubmitting,
    submitError: submitError || pipelineError,
    searchId,
    status,
    results,
    reset,
  };
}
