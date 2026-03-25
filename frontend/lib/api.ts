/** Backend API 호출 wrapper. */

import type {
  BriefInput,
  SearchResponse,
  SearchStatus,
  SearchResults,
  ClonePreview,
  CloneStatus,
  Prompt,
  Favorite,
  StorageInfo,
  ApiError,
  SkillSearchInput,
  SkillSearchResults,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiClient {
  private async request<T>(
    path: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${API_BASE}${path}`;
    const res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      ...options,
    });

    if (!res.ok) {
      const errorBody: ApiError = await res.json().catch(() => ({
        error: {
          code: "UNKNOWN",
          message: `HTTP ${res.status}: ${res.statusText}`,
        },
      }));
      throw errorBody;
    }

    return res.json();
  }

  // ─── Search ───

  async createSearch(brief: BriefInput): Promise<SearchResponse> {
    return this.request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ brief }),
    });
  }

  async getSearchStatus(searchId: string): Promise<SearchStatus> {
    return this.request<SearchStatus>(`/search/${searchId}/status`);
  }

  async getSearchResults(searchId: string): Promise<SearchResults> {
    return this.request<SearchResults>(`/search/${searchId}/results`);
  }

  async getRecentSearches(limit = 10): Promise<unknown[]> {
    return this.request(`/searches/recent?limit=${limit}`);
  }

  // ─── Clone ───

  async getClonePreview(candidateId: string): Promise<ClonePreview> {
    return this.request<ClonePreview>(`/clone/preview/${candidateId}`);
  }

  async startClone(candidateId: string): Promise<{ clone_id: string }> {
    return this.request("/clone", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId }),
    });
  }

  async getCloneStatus(cloneId: string): Promise<CloneStatus> {
    return this.request<CloneStatus>(`/clone/${cloneId}/status`);
  }

  async listClones(): Promise<unknown[]> {
    return this.request("/clone/list");
  }

  async getStorageInfo(): Promise<StorageInfo> {
    return this.request<StorageInfo>("/clone/storage-info");
  }

  async deleteClone(cloneId: string): Promise<void> {
    await this.request(`/clone/${cloneId}`, { method: "DELETE" });
  }

  // ─── Prompts ───

  async getPrompt(promptId: string): Promise<Prompt> {
    return this.request<Prompt>(`/prompts/${promptId}`);
  }

  async getEnhancedPrompt(promptId: string): Promise<Prompt> {
    return this.request<Prompt>(`/prompts/${promptId}/enhanced`);
  }

  async incrementCopyCount(promptId: string): Promise<void> {
    await this.request(`/prompts/${promptId}/copy`, { method: "POST" });
  }

  // ─── Favorites ───

  async listFavorites(): Promise<Favorite[]> {
    return this.request<Favorite[]>("/favorites");
  }

  async addFavorite(data: Omit<Favorite, "id" | "created_at">): Promise<Favorite> {
    return this.request<Favorite>("/favorites", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteFavorite(favoriteId: string): Promise<void> {
    await this.request(`/favorites/${favoriteId}`, { method: "DELETE" });
  }

  // ─── Skills ───

  async createSkillSearch(brief: SkillSearchInput): Promise<{ search_id: string; status: string }> {
    return this.request("/skills/search", {
      method: "POST",
      body: JSON.stringify({ brief }),
    });
  }

  async getSkillSearchStatus(searchId: string): Promise<SearchStatus> {
    return this.request<SearchStatus>(`/skills/search/${searchId}/status`);
  }

  async getSkillSearchResults(searchId: string): Promise<SkillSearchResults> {
    return this.request<SkillSearchResults>(`/skills/search/${searchId}/results`);
  }

  // ─── System ───

  async healthCheck(): Promise<Record<string, unknown>> {
    return this.request("/system/health");
  }

  async getRateLimit(): Promise<Record<string, unknown>> {
    return this.request("/system/rate-limit");
  }
}

export const api = new ApiClient();

/** SWR fetcher — GET 요청용 (에러 시 조용히 null 반환하지 않고 throw) */
export const fetcher = async (path: string) => {
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const msg = body?.error?.message ?? `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return res.json();
  } catch (err) {
    // 네트워크 에러 (서버 미응답)인 경우
    if (err instanceof TypeError && err.message.includes("fetch")) {
      throw new Error("서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.");
    }
    throw err;
  }
};
