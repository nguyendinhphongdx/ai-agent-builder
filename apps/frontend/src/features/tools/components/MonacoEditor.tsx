"use client";

import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import type { EditorProps } from "@monaco-editor/react";

const MonacoBase = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-50 items-center justify-center rounded-md border border-border bg-muted/30 text-xs text-muted-foreground">
      Loading editor…
    </div>
  ),
});

type MonacoOptions = NonNullable<EditorProps["options"]>;

interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  height?: number | string;
  readOnly?: boolean;
  options?: MonacoOptions;
}

export function MonacoEditor({
  value,
  onChange,
  language = "python",
  height = 280,
  readOnly = false,
  options,
}: MonacoEditorProps) {
  const { resolvedTheme } = useTheme();

  const editorOptions: MonacoOptions = {
    fontSize: 13,
    lineNumbers: "on",
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    wordWrap: "on",
    readOnly,
    padding: { top: 8, bottom: 8 },
    ...options,
  };

  return (
    <div className="overflow-hidden rounded-md border border-border">
      <MonacoBase
        height={height}
        language={language}
        value={value}
        theme={resolvedTheme === "dark" ? "vs-dark" : "vs"}
        options={editorOptions}
        onChange={(v) => onChange(v ?? "")}
      />
    </div>
  );
}
