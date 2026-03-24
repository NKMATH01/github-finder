"use client";

import { useCallback } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { Favorite } from "@/lib/types";

export function useFavorites() {
  const {
    data: favorites,
    error,
    mutate,
  } = useSWR<Favorite[]>("/favorites", fetcher);

  const addFavorite = useCallback(
    async (data: Omit<Favorite, "id" | "created_at">) => {
      try {
        const newFav = await api.addFavorite(data);
        // 낙관적 업데이트
        mutate((prev) => (prev ? [newFav, ...prev] : [newFav]), false);
      } catch {
        mutate(); // 실패 시 서버 데이터로 복원
      }
    },
    [mutate]
  );

  const removeFavorite = useCallback(
    async (favoriteId: string) => {
      // 낙관적 삭제
      mutate(
        (prev) => prev?.filter((f) => f.id !== favoriteId),
        false
      );
      try {
        await api.deleteFavorite(favoriteId);
      } catch {
        mutate(); // 실패 시 복원
      }
    },
    [mutate]
  );

  const isFavorite = useCallback(
    (repoUrl: string) => {
      return favorites?.some((f) => f.repo_url === repoUrl) ?? false;
    },
    [favorites]
  );

  return {
    favorites: favorites ?? [],
    isLoading: !favorites && !error,
    error,
    addFavorite,
    removeFavorite,
    isFavorite,
  };
}
