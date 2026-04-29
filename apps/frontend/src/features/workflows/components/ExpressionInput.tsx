"use client";

import { useCallback, useEffect, useId, useMemo, useRef } from "react";
import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import type { EditorProps, Monaco, OnMount } from "@monaco-editor/react";
import { useWorkflowRuns } from "../hooks/useWorkflows";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";
import { useOptionalWorkflowEditorContext } from "../lib/editor-context";
import { buildExpressionSchema } from "../lib/expression-schema";
import {
  clearExpressionContext,
  registerExpressionCompletion,
  setExpressionContext,
} from "../lib/expression-completion";

type EditorInstance = Parameters<OnMount>[0];
type EditorOptions = NonNullable<EditorProps["options"]>;

const MonacoBase = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-9 w-full animate-pulse rounded-md border border-border bg-muted/30" />
  ),
});

interface ExpressionInputProps {
  value: string;
  onChange: (value: string) => void;
  /** When true, render as a single-line field (no wrap, blocks Enter). */
  singleLine?: boolean;
  /** Multi-line height in px. Ignored when ``singleLine`` is true. */
  height?: number;
  placeholder?: string;
  className?: string;
  /** Node id this expression belongs to — drives upstream-aware autocomplete. */
  nodeId?: string;
}

const LANGUAGE_ID = "agentforge-expression";

/**
 * Single- or multi-line editor for templated strings.
 *
 * Highlights ``{{ ... }}`` blocks as Python (everything else is plain text)
 * and feeds Monaco an autocomplete provider that knows about the current
 * node's upstream output schema.
 */
export function ExpressionInput({
  value,
  onChange,
  singleLine = false,
  height = 100,
  placeholder,
  className,
  nodeId,
}: ExpressionInputProps) {
  const { resolvedTheme } = useTheme();
  const editorCtx = useOptionalWorkflowEditorContext();
  const workflowId = editorCtx?.workflowId;

  // Stable Monaco model URI — keys the per-instance schema in the completion
  // registry and ensures Monaco creates one model per ExpressionInput.
  const instanceId = useId();
  const modelPath = useMemo(
    () =>
      workflowId && nodeId
        ? `wf/${workflowId}/node/${nodeId}/${instanceId.replace(/[:]/g, "_")}.afe`
        : `wf/anon/${instanceId.replace(/[:]/g, "_")}.afe`,
    [workflowId, nodeId, instanceId],
  );

  // Schema derives from the editor graph + latest run. Recomputed when any of
  // those change so freshly-pinned outputs become available without a refetch.
  const nodes = useWorkflowEditorStore((s) => s.nodes);
  const edges = useWorkflowEditorStore((s) => s.edges);
  const { data: runs } = useWorkflowRuns(workflowId ?? "", 1);
  const latestRun = runs?.[0] ?? null;

  const schema = useMemo(
    () => (nodeId ? buildExpressionSchema(nodeId, nodes, edges, latestRun) : null),
    [nodeId, nodes, edges, latestRun],
  );

  const modelUriRef = useRef<string | null>(null);

  // Push the current schema into the completion registry whenever it changes.
  useEffect(() => {
    if (!schema || !modelUriRef.current) return;
    setExpressionContext(modelUriRef.current, { schema });
  }, [schema]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      if (modelUriRef.current) clearExpressionContext(modelUriRef.current);
    };
  }, []);

  const handleMount = useCallback<OnMount>(
    (editor: EditorInstance, monaco: Monaco) => {
      registerExpressionLanguage(monaco);
      registerExpressionCompletion(monaco, LANGUAGE_ID);

      modelUriRef.current = editor.getModel()?.uri.toString() ?? null;
      if (schema && modelUriRef.current) {
        setExpressionContext(modelUriRef.current, { schema });
      }

      if (singleLine) {
        editor.addCommand(monaco.KeyCode.Enter, () => undefined);
        editor.addCommand(monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => undefined);
        editor.onDidPaste(() => {
          const stripped = editor.getValue().replace(/\r?\n/g, " ");
          if (stripped !== editor.getValue()) editor.setValue(stripped);
        });
      }
    },
    [singleLine, schema],
  );

  const options: EditorOptions = singleLine
    ? {
        fontSize: 13,
        lineNumbers: "off",
        glyphMargin: false,
        folding: false,
        lineDecorationsWidth: 0,
        lineNumbersMinChars: 0,
        minimap: { enabled: false },
        overviewRulerLanes: 0,
        overviewRulerBorder: false,
        hideCursorInOverviewRuler: true,
        scrollbar: { vertical: "hidden", horizontal: "hidden", handleMouseWheel: false },
        scrollBeyondLastLine: false,
        scrollBeyondLastColumn: 0,
        renderLineHighlight: "none",
        wordWrap: "off",
        contextmenu: false,
        padding: { top: 6, bottom: 6 },
        fixedOverflowWidgets: true,
      }
    : {
        fontSize: 13,
        lineNumbers: "off",
        glyphMargin: false,
        folding: false,
        lineDecorationsWidth: 4,
        lineNumbersMinChars: 0,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        padding: { top: 8, bottom: 8 },
        contextmenu: false,
      };

  return (
    <div
      className={`overflow-hidden rounded-md border border-border bg-background focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/30 ${className ?? ""}`}
    >
      <MonacoBase
        path={modelPath}
        height={singleLine ? 32 : height}
        language={LANGUAGE_ID}
        value={value}
        onChange={(v) => onChange((singleLine ? (v ?? "").replace(/\r?\n/g, "") : v) ?? "")}
        onMount={handleMount}
        theme={resolvedTheme === "dark" ? "agentforge-dark" : "agentforge-light"}
        options={options}
      />
      {placeholder && !value && (
        <div className="pointer-events-none absolute -mt-7 ml-3 select-none text-xs text-muted-foreground/60">
          {placeholder}
        </div>
      )}
    </div>
  );
}

// ─── Monaco language registration (idempotent) ────────────────────────────────

let _registered = false;

function registerExpressionLanguage(monaco: Monaco) {
  if (_registered) return;
  _registered = true;

  monaco.languages.register({ id: LANGUAGE_ID });

  monaco.languages.setMonarchTokensProvider(LANGUAGE_ID, {
    defaultToken: "",
    tokenizer: {
      root: [
        [/\{\{/, { token: "delimiter.expression", next: "@expression" }],
        [/[^{]+/, "text"],
        [/\{(?!\{)/, "text"],
      ],
      expression: [
        [/\}\}/, { token: "delimiter.expression", next: "@pop" }],
        [/"([^"\\]|\\.)*"/, "string.expression"],
        [/'([^'\\]|\\.)*'/, "string.expression"],
        [/-?\d+(\.\d+)?/, "number.expression"],
        [
          /\b(json|item|items|nodes|vars|len|str|int|float|bool|min|max|sum|abs|round|sorted|if|else|and|or|not|in|True|False|None)\b/,
          "keyword.expression",
        ],
        [/[a-zA-Z_][\w]*/, "identifier.expression"],
        [/[+\-*/%=<>!&|^~?:.,(){}[\]]/, "operator.expression"],
        [/\s+/, ""],
      ],
    },
  });

  const expressionTokens = [
    { token: "delimiter.expression", foreground: "8b5cf6", fontStyle: "bold" },
    { token: "string.expression", foreground: "16a34a" },
    { token: "number.expression", foreground: "0ea5e9" },
    { token: "keyword.expression", foreground: "8b5cf6", fontStyle: "italic" },
    { token: "identifier.expression", foreground: "0284c7" },
    { token: "operator.expression", foreground: "9333ea" },
  ];

  monaco.editor.defineTheme("agentforge-light", {
    base: "vs",
    inherit: true,
    rules: expressionTokens,
    colors: {},
  });

  monaco.editor.defineTheme("agentforge-dark", {
    base: "vs-dark",
    inherit: true,
    rules: expressionTokens.map((r) => ({
      ...r,
      foreground: brightenForDark(r.foreground),
    })),
    colors: {},
  });
}

function brightenForDark(hex: string): string {
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  const blend = (c: number) => Math.min(255, Math.round(c + (255 - c) * 0.3));
  return [blend(r), blend(g), blend(b)]
    .map((c) => c.toString(16).padStart(2, "0"))
    .join("");
}
