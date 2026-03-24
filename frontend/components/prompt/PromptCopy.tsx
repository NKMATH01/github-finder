"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface PromptCopyProps {
  basicPrompt?: string;
  enhancedPrompt?: string;
  repoName: string;
}

export function PromptCopy({ basicPrompt, enhancedPrompt, repoName }: PromptCopyProps) {
  const [copied, setCopied] = useState<string | null>(null);

  const handleCopy = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(type);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // 폴백: textarea 선택
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(type);
      setTimeout(() => setCopied(null), 2000);
    }
  };

  const hasEnhanced = !!enhancedPrompt;

  return (
    <div className="rounded-lg border bg-white p-5 space-y-4">
      <p className="text-sm font-semibold text-gray-800">
        💡 Claude Code용 통합 프롬프트 — {repoName}
      </p>

      {hasEnhanced ? (
        <Tabs defaultValue="enhanced">
          <TabsList className="w-full">
            <TabsTrigger value="enhanced" className="flex-1 text-xs">
              강화 프롬프트 (리포트 반영)
            </TabsTrigger>
            <TabsTrigger value="basic" className="flex-1 text-xs">
              기본 프롬프트
            </TabsTrigger>
          </TabsList>

          <TabsContent value="enhanced">
            <div className="max-h-48 overflow-y-auto rounded bg-gray-50 p-3 text-xs text-gray-700 whitespace-pre-wrap font-mono">
              {enhancedPrompt}
            </div>
            <Button
              className="mt-3 w-full"
              size="sm"
              onClick={() => handleCopy(enhancedPrompt!, "enhanced")}
            >
              {copied === "enhanced" ? "✅ 복사됨!" : "📋 강화 프롬프트 복사"}
            </Button>
          </TabsContent>

          <TabsContent value="basic">
            <div className="max-h-48 overflow-y-auto rounded bg-gray-50 p-3 text-xs text-gray-700 whitespace-pre-wrap font-mono">
              {basicPrompt ?? "기본 프롬프트가 아직 생성되지 않았습니다."}
            </div>
            {basicPrompt && (
              <Button
                className="mt-3 w-full"
                size="sm"
                variant="outline"
                onClick={() => handleCopy(basicPrompt, "basic")}
              >
                {copied === "basic" ? "✅ 복사됨!" : "📋 기본 프롬프트 복사"}
              </Button>
            )}
          </TabsContent>
        </Tabs>
      ) : (
        <>
          <div className="max-h-48 overflow-y-auto rounded bg-gray-50 p-3 text-xs text-gray-700 whitespace-pre-wrap font-mono">
            {basicPrompt ?? "프롬프트가 아직 생성되지 않았습니다."}
          </div>
          {basicPrompt && (
            <Button
              className="mt-3 w-full"
              size="sm"
              onClick={() => handleCopy(basicPrompt, "basic")}
            >
              {copied === "basic" ? "✅ 복사됨!" : "💡 Claude Code용 프롬프트 복사"}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
