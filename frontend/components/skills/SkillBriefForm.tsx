"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { SkillSearchInput } from "@/hooks/useSkillSearch";

const QUICK_EXAMPLES = [
  { label: "📝 코드 리뷰", query: "PR 코드를 자동으로 리뷰하고 피드백을 남기는 스킬" },
  { label: "🔧 Git 자동화", query: "커밋 메시지 자동 생성, 브랜치 관리 등 Git 워크플로우 자동화" },
  { label: "🏗 MCP 서버", query: "외부 서비스와 연동하는 MCP 서버를 자동으로 생성하는 스킬" },
  { label: "📊 데이터 분석", query: "CSV/JSON 데이터를 분석하고 시각화 코드를 생성하는 스킬" },
];

interface SkillBriefFormProps {
  onSubmit: (brief: SkillSearchInput) => void;
  isLoading?: boolean;
}

export function SkillBriefForm({ onSubmit, isLoading }: SkillBriefFormProps) {
  const [query, setQuery] = useState("");
  const [projectStack, setProjectStack] = useState("");
  const [targetTool, setTargetTool] = useState("claude_code");

  const handleSubmit = () => {
    if (!query.trim()) return;
    onSubmit({
      query_ko: query.trim(),
      project_stack: projectStack.trim() || undefined,
      target_tool: targetTool,
    });
  };

  const isValid = query.trim().length > 0;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* 히어로 */}
      <div className="text-center space-y-3">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 shadow-lg shadow-violet-500/20">
          <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.25 6.087c0-.355.186-.676.401-.959.221-.29.349-.634.349-1.003 0-1.036-1.007-1.875-2.25-1.875s-2.25.84-2.25 1.875c0 .369.128.713.349 1.003.215.283.401.604.401.959v0a.64.64 0 01-.657.643 48.39 48.39 0 01-4.163-.3c.186 1.613.293 3.25.315 4.907a.656.656 0 01-.658.663v0c-.355 0-.676-.186-.959-.401a1.647 1.647 0 00-1.003-.349c-1.036 0-1.875 1.007-1.875 2.25s.84 2.25 1.875 2.25c.369 0 .713-.128 1.003-.349.283-.215.604-.401.959-.401v0c.31 0 .555.26.532.57a48.039 48.039 0 01-.642 5.056c1.518.19 3.058.309 4.616.354a.64.64 0 00.657-.643v0c0-.355-.186-.676-.401-.959a1.647 1.647 0 01-.349-1.003c0-1.035 1.008-1.875 2.25-1.875 1.243 0 2.25.84 2.25 1.875 0 .369-.128.713-.349 1.003-.215.283-.4.604-.4.959v0c0 .333.277.599.61.58a48.1 48.1 0 005.427-.63 48.05 48.05 0 00.582-4.717.532.532 0 00-.533-.57v0c-.355 0-.676.186-.959.401-.29.221-.634.349-1.003.349-1.035 0-1.875-1.007-1.875-2.25s.84-2.25 1.875-2.25c.37 0 .713.128 1.003.349.283.215.604.401.96.401v0a.656.656 0 00.658-.663 48.422 48.422 0 00-.37-5.36c-1.886.342-3.81.574-5.766.689a.578.578 0 01-.61-.58v0z" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold tracking-tight text-slate-900">
          어떤 스킬을 찾고 계신가요?
        </h2>
        <p className="text-base text-slate-500 max-w-md mx-auto">
          한국어로 설명하면 SkillsMP에서 최적의 Claude Code 스킬 3개를 찾아 비교해드립니다
        </p>
      </div>

      {/* 빠른 예시 */}
      <div className="flex justify-center gap-2 flex-wrap">
        {QUICK_EXAMPLES.map((example) => (
          <button
            key={example.label}
            onClick={() => setQuery(example.query)}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm transition-all hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700 hover:shadow-md active:scale-95"
          >
            {example.label}
          </button>
        ))}
      </div>

      {/* 폼 */}
      <div className="rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg shadow-slate-200/50 space-y-6">

        {/* 1. 원하는 기능 */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-violet-100 text-xs font-bold text-violet-600">1</span>
            원하는 기능
            <span className="text-red-400 text-xs">필수</span>
          </label>
          <Textarea
            placeholder="예: 코드 리뷰를 자동으로 해주고, PR에 피드백을 남기는 스킬"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            className="resize-none rounded-xl border-slate-200 bg-slate-50/50 focus:bg-white focus:border-violet-300 focus:ring-violet-200 transition-colors text-sm"
          />
        </div>

        {/* 2. 프로젝트 스택 */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">2</span>
            프로젝트 스택
            <span className="text-slate-400 text-xs">선택</span>
          </label>
          <Input
            placeholder="예: Next.js, Python, FastAPI"
            value={projectStack}
            onChange={(e) => setProjectStack(e.target.value)}
            className="rounded-xl border-slate-200 bg-slate-50/50 text-sm"
          />
        </div>

        {/* 3. 대상 도구 */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">3</span>
            대상 도구
            <span className="text-slate-400 text-xs">선택</span>
          </label>
          <Select value={targetTool} onValueChange={setTargetTool}>
            <SelectTrigger className="rounded-xl border-slate-200 bg-slate-50/50 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="claude_code">Claude Code</SelectItem>
              <SelectItem value="codex_cli">Codex CLI</SelectItem>
              <SelectItem value="all">모두</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 제출 버튼 */}
        <Button
          className="w-full h-12 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-semibold shadow-lg shadow-violet-500/25 hover:shadow-xl hover:shadow-violet-500/30 hover:brightness-110 transition-all disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed"
          size="lg"
          onClick={handleSubmit}
          disabled={!isValid || isLoading}
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              검색 중...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" /></svg>
              SkillsMP에서 찾기
            </span>
          )}
        </Button>
      </div>
    </div>
  );
}
