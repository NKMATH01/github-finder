"use client";

import { useFavorites } from "@/hooks/useFavorites";
import { Button } from "@/components/ui/button";

export function Favorites() {
  const { favorites, removeFavorite } = useFavorites();

  if (favorites.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        즐겨찾기
      </p>
      {favorites.slice(0, 8).map((fav) => (
        <div
          key={fav.id}
          className="flex items-center justify-between rounded-md border px-3 py-2 text-xs"
        >
          <div className="flex-1 min-w-0">
            <p className="truncate font-medium text-gray-700">
              ⭐ {fav.repo_name}
            </p>
            {fav.category && (
              <p className="text-gray-400">{fav.category}</p>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="ml-2 h-6 w-6 p-0 text-gray-400 hover:text-red-500"
            onClick={() => removeFavorite(fav.id)}
          >
            ×
          </Button>
        </div>
      ))}
    </div>
  );
}
