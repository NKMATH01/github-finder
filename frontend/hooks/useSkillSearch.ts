"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { SearchStatus, SSEEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface SkillCandidate {
  skill_id: string;
  skill_name: string;
  github_url: string;
  skill_path: string;
  author: string;
  stars: number;
  category: string;
  category_reason: string;
  total_score: number;
  score_detail: {
    feature_match: number;
    quality: number;
    compatibility: number;
    community_trust: number;
    install_ease: number;
  };
  skill_md_preview: string;
  pros: string[];
  cons: string[];
  warnings: string[];
  install_command?: string;
}

export interface SkillSearchResults {
  search_id: string;
  query_ko: string;
  candidates: SkillCandidate[];
}

export interface SkillSearchInput {
  query_ko: string;
  project_stack?: string;
  target_tool?: string;
}

export function useSkillSearch() {
  const [searchId, setSearchId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sseStatus, setSseStatus] = useState<SearchStatus | null>(null);
  const [sseConnected, setSseConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // SSE 연결
  useEffect(() => {
    if (!searchId) return;

    const es = new EventSource(`${API_BASE}/skills/search/${searchId}/stream`);
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

        if (["completed", "failed", "no_results"].includes(data.status)) {
          es.close();
          setSseConnected(false);
        }
      } catch {
        // JSON parse error 무시
      }
    };

    es.onerror = () => {
      setSseConnected(false);
    };

    return () => {
      es.close();
      setSseConnected(false);
    };
  }, [searchId]);

  // SSE 실패 시 폴링 fallback
  const shouldPoll =
    searchId && !sseConnected && sseStatus?.status !== "completed" && sseStatus?.status !== "failed";
  const { data: polledStatus } = useSWR<SearchStatus>(
    shouldPoll ? `/skills/search/${searchId}/status` : null,
    fetcher,
    {
      refreshInterval: 2000,
      revalidateOnFocus: false,
      errorRetryCount: 5,
      shouldRetryOnError: true,
      onError: () => {},
    }
  );

  const status = sseStatus || polledStatus || null;
  const isCompleted = status?.status === "completed";
  const isFailed = status?.status === "failed" || status?.status === "no_results";

  const { data: results } = useSWR<SkillSearchResults>(
    searchId && isCompleted ? `/skills/search/${searchId}/results` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      errorRetryCount: 3,
      onError: () => {},
    }
  );

  const pipelineError = isFailed ? (status?.message || "스킬 검색에 실패했습니다.") : null;

  const submitBrief = useCallback(async (brief: SkillSearchInput) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSseStatus(null);
    try {
      const res = await fetch(`${API_BASE}/skills/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error?.message || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setSearchId(data.search_id);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "스킬 검색 요청에 실패했습니다.");
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
