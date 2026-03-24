"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { StorageInfo as StorageInfoType } from "@/lib/types";

export function StorageInfo() {
  const { data } = useSWR<StorageInfoType>(
    "/clone/storage-info",
    fetcher,
    { revalidateOnFocus: false, errorRetryCount: 0, shouldRetryOnError: false }
  );

  if (!data || data.repo_count === 0) return null;

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        클론 저장소
      </p>
      <div className="rounded-md border px-3 py-2 text-xs text-gray-600">
        <p>
          📁 총 {data.total_size_mb.toFixed(1)}MB / {data.repo_count}개 레포
        </p>
        {data.repos.slice(0, 3).map((repo, i) => (
          <p key={i} className="ml-2 text-gray-400 truncate">
            · {repo.name} ({repo.size_mb}MB)
          </p>
        ))}
      </div>
    </div>
  );
}
