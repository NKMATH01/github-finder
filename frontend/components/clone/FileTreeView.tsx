"use client";

import { useState } from "react";
import type { FileTreeNode } from "@/lib/types";

interface FileTreeViewProps {
  tree: FileTreeNode[];
  keyFiles?: string[];
}

export function FileTreeView({ tree, keyFiles = [] }: FileTreeViewProps) {
  return (
    <div className="rounded-lg border bg-white p-4">
      <p className="mb-3 text-sm font-medium text-gray-700">📁 파일 트리</p>
      <div className="max-h-64 overflow-y-auto font-mono text-xs">
        {tree.map((node, i) => (
          <TreeNode key={i} node={node} depth={0} keyFiles={keyFiles} />
        ))}
      </div>
    </div>
  );
}

function TreeNode({
  node,
  depth,
  keyFiles,
}: {
  node: FileTreeNode;
  depth: number;
  keyFiles: string[];
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isKey = keyFiles.some((kf) => kf.endsWith(node.name));
  const indent = depth * 16;

  if (node.type === "directory") {
    return (
      <div>
        <div
          className="flex cursor-pointer items-center gap-1 rounded px-1 py-0.5 hover:bg-gray-100"
          style={{ paddingLeft: indent }}
          onClick={() => setExpanded(!expanded)}
        >
          <span className="text-gray-400">{expanded ? "▼" : "▶"}</span>
          <span className="text-blue-600">{node.name}/</span>
        </div>
        {expanded &&
          node.children?.map((child, i) => (
            <TreeNode key={i} node={child} depth={depth + 1} keyFiles={keyFiles} />
          ))}
      </div>
    );
  }

  return (
    <div
      className={`flex items-center gap-1 rounded px-1 py-0.5 ${
        isKey ? "bg-yellow-50 font-semibold text-yellow-800" : "text-gray-600"
      }`}
      style={{ paddingLeft: indent }}
    >
      <span className="text-gray-300">·</span>
      <span>{node.name}</span>
      {isKey && <span className="ml-1 text-[10px] text-yellow-600">← 핵심</span>}
      {node.size != null && (
        <span className="ml-auto text-gray-300">
          {node.size > 1024 ? `${(node.size / 1024).toFixed(0)}KB` : `${node.size}B`}
        </span>
      )}
    </div>
  );
}
