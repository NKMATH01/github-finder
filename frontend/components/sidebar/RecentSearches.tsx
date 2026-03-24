"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface RecentSearch {
  id: string;
  query_ko: string;
  candidate_count: number;
  status: string;
  created_at: string;
}

interface RecentSearchesProps {
  onSelect: (searchId: string) => void;
}

export function RecentSearches({ onSelect }: RecentSearchesProps) {
  const { data: searches } = useSWR<RecentSearch[]>(
    "/searches/recent?limit=5",
    fetcher,
    { revalidateOnFocus: false, errorRetryCount: 0, shouldRetryOnError: false }
  );

  if (!searches || searches.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        최근 검색
      </p>
      {searches.map((s) => (
        <button
          key={s.id}
          className="flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-xs hover:bg-gray-50 transition-colors"
          onClick={() => onSelect(s.id)}
        >
          <div className="flex-1 min-w-0">
            <p className="truncate font-medium text-gray-700">{s.query_ko}</p>
            <p className="text-gray-400">
              {new Date(s.created_at).toLocaleDateString("ko-KR", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          </div>
          {s.status === "completed" && (
            <span className="ml-2 shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700">
              {s.candidate_count}개
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
