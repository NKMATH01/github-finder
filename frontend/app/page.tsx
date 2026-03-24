"use client";

import { useState } from "react";
import type { AppView, BriefInput, Candidate } from "@/lib/types";
import { useSearch } from "@/hooks/useSearch";
import { useClone } from "@/hooks/useClone";
import { useFavorites } from "@/hooks/useFavorites";
import { BriefForm } from "@/components/brief/BriefForm";
import { CandidateCard } from "@/components/results/CandidateCard";
import { ComparisonTable } from "@/components/results/ComparisonTable";
import { DetailModal } from "@/components/results/DetailModal";
import { FileTreeView } from "@/components/clone/FileTreeView";
import { StructureReport } from "@/components/clone/StructureReport";
import { PromptCopy } from "@/components/prompt/PromptCopy";
import { RecentSearches } from "@/components/sidebar/RecentSearches";
import { Favorites } from "@/components/sidebar/Favorites";
import { StorageInfo } from "@/components/sidebar/StorageInfo";
import { ErrorDisplay } from "@/components/common/ErrorDisplay";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { SearchProgress } from "@/components/SearchProgress";

export default function Home() {
  const [view, setView] = useState<AppView>("brief");
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [detailCandidate, setDetailCandidate] = useState<Candidate | null>(null);

  const search = useSearch();
  const clone = useClone();
  const favorites = useFavorites();

  const handleSubmit = async (brief: BriefInput) => {
    setView("loading");
    await search.submitBrief(brief);
  };

  if (view === "loading" && search.results) setView("results");
  // 실패/결과없음 시 에러 메시지가 submitError로 전달되어 로딩 화면에서 표시됨

  const handleClone = async (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    setView("clone");
    await clone.startClone(candidate.id);
  };

  const handleCopyPrompt = async (candidate: Candidate) => {
    const text = `## ${candidate.repo_name} 통합 프롬프트\n\n레포: ${candidate.repo_url}\n핵심 파일: ${candidate.key_files.map(f => f.path).join(", ")}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch { /* ignore */ }
  };

  const handleToggleFavorite = (candidate: Candidate) => {
    if (favorites.isFavorite(candidate.repo_url)) {
      const fav = favorites.favorites.find(f => f.repo_url === candidate.repo_url);
      if (fav) favorites.removeFavorite(fav.id);
    } else {
      favorites.addFavorite({
        repo_url: candidate.repo_url,
        repo_name: candidate.repo_name,
        category: candidate.category,
      });
    }
  };

  const handleBack = () => {
    if (view === "clone") { setView("results"); clone.reset(); }
    else if (view === "results" || view === "loading") { setView("brief"); search.reset(); }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
      {/* 헤더 */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 shadow-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <button
            className="flex items-center gap-3 transition-opacity hover:opacity-80"
            onClick={() => { setView("brief"); search.reset(); clone.reset(); }}
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 text-white text-sm font-bold shadow-lg shadow-blue-500/25">
              G
            </div>
            <div>
              <h1 className="text-base font-semibold text-white tracking-tight">
                GitHub 기능 조달 워크벤치
              </h1>
              <p className="text-[10px] text-slate-400 -mt-0.5">Open Source Discovery Engine</p>
            </div>
          </button>
          <div className="flex items-center gap-3">
            {view !== "brief" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleBack}
                className="text-slate-300 hover:text-white hover:bg-white/10"
              >
                <svg className="mr-1.5 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
                뒤로
              </Button>
            )}
            <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-medium text-slate-400">
              v0.1
            </span>
          </div>
        </div>
      </header>

      {/* 메인 */}
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="flex gap-8">
          {/* 사이드바 */}
          {view === "brief" && (
            <aside className="hidden w-72 shrink-0 space-y-6 lg:block">
              <div className="rounded-2xl border border-slate-200/60 bg-white/80 backdrop-blur-sm p-5 shadow-sm">
                <RecentSearches onSelect={() => {}} />
              </div>
              <div className="rounded-2xl border border-slate-200/60 bg-white/80 backdrop-blur-sm p-5 shadow-sm">
                <Favorites />
              </div>
              <div className="rounded-2xl border border-slate-200/60 bg-white/80 backdrop-blur-sm p-5 shadow-sm">
                <StorageInfo />
              </div>
            </aside>
          )}

          <div className="flex-1 min-w-0">
            {/* 브리프 입력 */}
            {view === "brief" && (
              <BriefForm onSubmit={handleSubmit} isLoading={search.isSubmitting} />
            )}

            {/* 로딩 (SSE 실시간 진행률) */}
            {view === "loading" && (
              <div className="flex min-h-[60vh] items-center justify-center">
                {search.submitError ? (
                  <div className="w-full max-w-md">
                    <ErrorDisplay error={search.submitError} onRetry={() => setView("brief")} />
                  </div>
                ) : search.status ? (
                  <SearchProgress status={search.status} />
                ) : (
                  <div className="w-full max-w-md space-y-8 text-center">
                    <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/10 to-violet-500/10">
                      <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-slate-200 border-t-blue-600" />
                    </div>
                    <p className="text-sm text-slate-500">연결 중...</p>
                  </div>
                )}
              </div>
            )}

            {/* 결과 비교 */}
            {view === "results" && search.results && (
              <div className="space-y-8">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">
                      검색 결과
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      {search.results.candidates.length}개의 최적 후보를 찾았습니다
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-1.5 self-start rounded-full bg-amber-50 border border-amber-200/60 px-3 py-1.5 text-xs font-medium text-amber-700">
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
                    LLM 분석 기반 (실행 미검증)
                  </span>
                </div>

                <div className="grid gap-5 md:grid-cols-3">
                  {search.results.candidates.map((candidate) => (
                    <CandidateCard
                      key={candidate.id}
                      candidate={candidate}
                      onClone={handleClone}
                      onCopyPrompt={handleCopyPrompt}
                      onToggleFavorite={handleToggleFavorite}
                      isFavorite={favorites.isFavorite(candidate.repo_url)}
                      onShowDetail={(c) => setDetailCandidate(c)}
                    />
                  ))}
                </div>

                <ComparisonTable candidates={search.results.candidates} />

                <p className="text-center text-sm text-slate-400">
                  이 중에서 프로젝트 상황에 맞는 후보를 골라 테스트해보세요.
                </p>
              </div>
            )}

            {/* 클론 + 분석 */}
            {view === "clone" && selectedCandidate && (
              <div className="mx-auto max-w-3xl space-y-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10">
                    <span className="text-lg">📦</span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">{selectedCandidate.repo_name}</h2>
                    <p className="text-xs text-slate-500">레포 클론 + 구조 분석</p>
                  </div>
                </div>

                {clone.cloneError && (
                  <ErrorDisplay error={clone.cloneError} onRetry={() => clone.startClone(selectedCandidate.id)} />
                )}

                {clone.cloneStatus && (
                  <div className="rounded-2xl border border-slate-200/60 bg-white p-6 shadow-sm space-y-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {clone.cloneStatus.status !== "completed" && clone.cloneStatus.status !== "failed" && (
                          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
                        )}
                        {clone.cloneStatus.status === "completed" && (
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 text-sm">✓</div>
                        )}
                        {clone.cloneStatus.status === "failed" && (
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 text-red-600 text-sm">✗</div>
                        )}
                        <p className="font-medium text-slate-800">
                          {clone.cloneStatus.status === "cloning" && "레포 클론 중..."}
                          {clone.cloneStatus.status === "scanning" && "파일 트리 스캔 중..."}
                          {clone.cloneStatus.status === "analyzing" && "AI 구조 분석 중..."}
                          {clone.cloneStatus.status === "completed" && "클론 + 분석 완료"}
                          {clone.cloneStatus.status === "failed" && "작업 실패"}
                        </p>
                      </div>
                      <span className="text-sm font-medium text-slate-400">{clone.cloneStatus.progress}%</span>
                    </div>
                    <Progress value={clone.cloneStatus.progress} className="h-1.5" />

                    {clone.cloneStatus.status === "completed" && (
                      <div className="space-y-5 pt-2">
                        <div className="flex gap-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
                          <span>📁 {clone.cloneStatus.file_count}개 파일</span>
                          <span className="text-slate-300">|</span>
                          <span>💻 {clone.cloneStatus.code_file_count}개 코드</span>
                          <span className="text-slate-300">|</span>
                          <span>📦 {clone.cloneStatus.total_size_mb?.toFixed(1)}MB</span>
                        </div>

                        {clone.cloneStatus.file_tree && (
                          <FileTreeView
                            tree={clone.cloneStatus.file_tree}
                            keyFiles={selectedCandidate?.key_files.map(f => f.path) ?? []}
                          />
                        )}

                        <StructureReport
                          safe={clone.cloneStatus.integration_safe}
                          risky={clone.cloneStatus.integration_risky}
                          fail={clone.cloneStatus.integration_fail}
                        />

                        <PromptCopy
                          basicPrompt={undefined}
                          enhancedPrompt={clone.cloneStatus.enhanced_prompt ?? undefined}
                          repoName={selectedCandidate?.repo_name ?? ""}
                        />
                      </div>
                    )}

                    {clone.cloneStatus.status === "failed" && (
                      <div className="rounded-xl bg-red-50 border border-red-200/60 p-4 text-sm text-red-700">
                        {clone.cloneStatus.error_message ?? "클론에 실패했습니다."}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      <DetailModal
        candidate={detailCandidate}
        open={!!detailCandidate}
        onClose={() => setDetailCandidate(null)}
      />

      {/* 푸터 */}
      <footer className="border-t border-slate-200/60 bg-white/50 backdrop-blur-sm mt-20">
        <div className="mx-auto max-w-7xl px-6 py-6 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            GitHub 기능 조달 워크벤치 v0.1 — 개인용 로컬 도구
          </p>
          <p className="text-xs text-slate-300">
            Powered by GPT-4o + GitHub API
          </p>
        </div>
      </footer>
    </div>
  );
}
