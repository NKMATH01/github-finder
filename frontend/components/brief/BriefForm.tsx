"use client";

import { useState } from "react";
import type { BriefInput } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";

const STACK_OPTIONS = [
  "Next.js", "React", "Vue", "Angular", "Svelte",
  "Python", "FastAPI", "Django", "Flask",
  "Node.js", "Express", "TypeScript",
  "Java", "Spring", "Go", "Rust",
  "PostgreSQL", "MySQL", "MongoDB", "Supabase", "Firebase",
];

const QUICK_EXAMPLES = [
  { label: "👁 시선 추적", brief: { goal_description: "학생들이 웹캠을 통해 수업에 집중하고 있는지 시선을 추적하여 실시간으로 판단하는 기능", project_stack: ["Next.js", "FastAPI", "PostgreSQL"], execution_environment: "server" as const, priority: "speed" as const } },
  { label: "🎤 음성 인식", brief: { goal_description: "실시간 음성을 텍스트로 변환하는 STT 기능", project_stack: ["React", "Node.js"], execution_environment: "web_browser" as const, priority: "accuracy" as const } },
  { label: "📄 OCR 텍스트", brief: { goal_description: "이미지에서 텍스트를 추출하는 OCR 기능", project_stack: ["Python", "FastAPI"], execution_environment: "server" as const, priority: "balanced" as const } },
  { label: "📊 PDF 생성", brief: { goal_description: "데이터를 기반으로 PDF 리포트를 자동 생성하는 기능", project_stack: ["Python", "FastAPI"], execution_environment: "server" as const, priority: "speed" as const } },
];

interface BriefFormProps {
  onSubmit: (brief: BriefInput) => void;
  isLoading?: boolean;
}

export function BriefForm({ onSubmit, isLoading }: BriefFormProps) {
  const [goal, setGoal] = useState("");
  const [selectedStacks, setSelectedStacks] = useState<string[]>([]);
  const [customStack, setCustomStack] = useState("");
  const [environment, setEnvironment] = useState<string>("any");
  const [priority, setPriority] = useState([50]);
  const [referenceRepo, setReferenceRepo] = useState("");
  const [additionalConditions, setAdditionalConditions] = useState("");
  const [showOptional, setShowOptional] = useState(false);

  const toggleStack = (stack: string) => {
    setSelectedStacks((prev) =>
      prev.includes(stack) ? prev.filter((s) => s !== stack) : [...prev, stack]
    );
  };

  const addCustomStack = () => {
    const trimmed = customStack.trim();
    if (trimmed && !selectedStacks.includes(trimmed)) {
      setSelectedStacks((prev) => [...prev, trimmed]);
      setCustomStack("");
    }
  };

  const handleSubmit = () => {
    if (!goal.trim()) return;
    const priorityValue = priority[0] < 33 ? "accuracy" : priority[0] > 66 ? "speed" : "balanced";
    onSubmit({
      goal_description: goal.trim(),
      project_stack: selectedStacks.length > 0 ? selectedStacks : ["any"],
      execution_environment: environment as BriefInput["execution_environment"],
      priority: priorityValue,
      reference_repo: referenceRepo.trim() || undefined,
      additional_conditions: additionalConditions.trim() || undefined,
    });
  };

  const loadExample = (example: typeof QUICK_EXAMPLES[0]) => {
    setGoal(example.brief.goal_description);
    setSelectedStacks(example.brief.project_stack);
    setEnvironment(example.brief.execution_environment);
    setPriority([example.brief.priority === "accuracy" ? 15 : example.brief.priority === "speed" ? 85 : 50]);
  };

  const isValid = goal.trim().length > 0;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* 히어로 */}
      <div className="text-center space-y-3">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 shadow-lg shadow-blue-500/20">
          <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold tracking-tight text-slate-900">
          어떤 기능을 찾고 계신가요?
        </h2>
        <p className="text-base text-slate-500 max-w-md mx-auto">
          한국어로 설명하면 GitHub에서 최적의 오픈소스 3개를 찾아 비교해드립니다
        </p>
      </div>

      {/* 빠른 예시 */}
      <div className="flex justify-center gap-2 flex-wrap">
        {QUICK_EXAMPLES.map((example) => (
          <button
            key={example.label}
            onClick={() => loadExample(example)}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm transition-all hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 hover:shadow-md active:scale-95"
          >
            {example.label}
          </button>
        ))}
      </div>

      {/* 폼 */}
      <div className="rounded-2xl border border-slate-200/60 bg-white p-8 shadow-lg shadow-slate-200/50 space-y-6">

        {/* 1. 목표 기능 */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-100 text-xs font-bold text-blue-600">1</span>
            목표 기능
            <span className="text-red-400 text-xs">필수</span>
          </label>
          <Textarea
            placeholder="예: 학생들이 웹캠을 통해 수업에 집중하고 있는지 시선을 추적하여 실시간으로 판단하는 기능"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            rows={3}
            className="resize-none rounded-xl border-slate-200 bg-slate-50/50 focus:bg-white focus:border-blue-300 focus:ring-blue-200 transition-colors text-sm"
          />
        </div>

        {/* 2. 프로젝트 스택 */}
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">2</span>
            프로젝트 스택
            <span className="text-slate-400 text-xs">선택 — 모르면 비워두세요</span>
          </label>
          <button
            onClick={() => setSelectedStacks([])}
            className={`w-full rounded-xl border p-3 text-left text-sm transition-all ${
              selectedStacks.length === 0
                ? "border-blue-300 bg-blue-50 text-blue-700 ring-1 ring-blue-200"
                : "border-slate-200 bg-white text-slate-500 hover:border-slate-300"
            }`}
          >
            🤖 잘 모르겠어요 — AI가 알아서 추천해주세요
          </button>
          <div className="flex flex-wrap gap-1.5">
            {STACK_OPTIONS.map((stack) => (
              <button
                key={stack}
                onClick={() => toggleStack(stack)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  selectedStacks.includes(stack)
                    ? "bg-blue-600 text-white shadow-sm shadow-blue-300"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {stack}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="직접 입력 (Enter)"
              value={customStack}
              onChange={(e) => setCustomStack(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addCustomStack()}
              className="flex-1 rounded-xl border-slate-200 bg-slate-50/50 text-sm"
            />
            <Button variant="outline" size="sm" onClick={addCustomStack} className="rounded-xl">
              추가
            </Button>
          </div>
          {selectedStacks.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {selectedStacks.map((s) => (
                <Badge key={s} className="rounded-lg bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 cursor-pointer" onClick={() => toggleStack(s)}>
                  {s} ×
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* 3. 실행 환경 */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-100 text-xs font-bold text-blue-600">3</span>
            실행 환경
            <span className="text-red-400 text-xs">필수</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { value: "web_browser", label: "웹 브라우저", desc: "프론트엔드 직접 실행", icon: "🌐" },
              { value: "server", label: "서버", desc: "백엔드에서 처리", icon: "🖥" },
              { value: "local_app", label: "로컬 앱", desc: "Electron 등", icon: "💻" },
              { value: "any", label: "상관없음", desc: "환경 무관", icon: "✨" },
            ].map((env) => (
              <button
                key={env.value}
                onClick={() => setEnvironment(env.value)}
                className={`flex items-center gap-3 rounded-xl border p-3 text-left transition-all ${
                  environment === env.value
                    ? "border-blue-300 bg-blue-50 ring-1 ring-blue-200"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <span className="text-lg">{env.icon}</span>
                <div>
                  <p className={`text-sm font-medium ${environment === env.value ? "text-blue-700" : "text-slate-700"}`}>{env.label}</p>
                  <p className="text-[11px] text-slate-400">{env.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 선택 입력 토글 */}
        <button
          onClick={() => setShowOptional(!showOptional)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          <svg className={`h-4 w-4 transition-transform ${showOptional ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
          선택 입력으로 정밀도 향상
        </button>

        {showOptional && (
          <div className="space-y-5 rounded-xl bg-slate-50/70 p-5 border border-slate-100">
            {/* 4. 우선순위 */}
            <div className="space-y-3">
              <label className="text-sm font-medium text-slate-600">우선순위</label>
              <div className="flex items-center gap-4">
                <span className="text-xs text-slate-400 w-12">정확도</span>
                <Slider
                  value={priority}
                  onValueChange={(v) => setPriority(Array.isArray(v) ? v as number[] : [v as number])}
                  max={100}
                  step={1}
                  className="flex-1"
                />
                <span className="text-xs text-slate-400 w-8">속도</span>
              </div>
            </div>

            {/* 5. 참고 레포 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-600">참고 레포</label>
              <Input
                placeholder="https://github.com/owner/repo"
                value={referenceRepo}
                onChange={(e) => setReferenceRepo(e.target.value)}
                className="rounded-xl border-slate-200 bg-white text-sm"
              />
            </div>

            {/* 6. 추가 조건 */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-600">추가 조건</label>
              <Textarea
                placeholder="예: GPU 없이 실시간 처리 가능, 서버 없이 브라우저에서만 동작"
                value={additionalConditions}
                onChange={(e) => setAdditionalConditions(e.target.value)}
                rows={2}
                className="resize-none rounded-xl border-slate-200 bg-white text-sm"
              />
            </div>
          </div>
        )}

        {/* 제출 버튼 */}
        <Button
          className="w-full h-12 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 text-white font-semibold shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30 hover:brightness-110 transition-all disabled:opacity-40 disabled:shadow-none disabled:cursor-not-allowed"
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
              GitHub에서 찾기
            </span>
          )}
        </Button>

        {/* 미입력 안내 */}
        {!isValid && (
          <div className="flex items-center gap-2 rounded-xl bg-amber-50 border border-amber-200/60 px-4 py-3 text-xs text-amber-700">
            <svg className="h-4 w-4 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
            <span>어떤 기능을 찾고 싶은지 설명해주세요 (스택은 몰라도 OK!)</span>
            <span className="ml-auto text-amber-500">또는 위의 빠른 예시를 클릭하세요 ↑</span>
          </div>
        )}
      </div>
    </div>
  );
}
