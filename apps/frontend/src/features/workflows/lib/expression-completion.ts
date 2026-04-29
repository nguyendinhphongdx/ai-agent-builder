/**
 * Monaco completion provider for the `agentforge-expression` language.
 *
 * One global provider is registered; per-instance context (current schema) is
 * looked up by Monaco model URI. Each ExpressionInput instance writes its own
 * snapshot into ``contextRegistry`` on mount and clears it on unmount.
 */
import type { Monaco } from "@monaco-editor/react";
import type { ExpressionSchema, UpstreamNodeSchema } from "./expression-schema";

// Monaco's `editor.ITextModel` and `Position` types come transitively through
// `@monaco-editor/react`. Extract them from the registerCompletionItemProvider
// signature to avoid pulling in `monaco-editor` as a direct dep.
type CompletionProvider = Parameters<
  Monaco["languages"]["registerCompletionItemProvider"]
>[1];
type ProvideArgs = Parameters<NonNullable<CompletionProvider["provideCompletionItems"]>>;
type ITextModel = ProvideArgs[0];
type IPosition = ProvideArgs[1];

interface ExpressionContext {
  schema: ExpressionSchema;
}

const contextRegistry = new Map<string, ExpressionContext>();

let _completionRegistered = false;

export function setExpressionContext(uri: string, ctx: ExpressionContext): void {
  contextRegistry.set(uri, ctx);
}

export function clearExpressionContext(uri: string): void {
  contextRegistry.delete(uri);
}

const TOP_LEVEL_NAMES = [
  { label: "json", detail: "current input item", insertText: "json" },
  { label: "item", detail: "alias of json", insertText: "item" },
  { label: "items", detail: "list of input items", insertText: "items" },
  { label: "nodes", detail: 'upstream outputs — nodes["LABEL"][0].field', insertText: "nodes" },
  { label: "vars", detail: "workflow variables", insertText: "vars" },
];

const BUILTIN_FUNCTIONS = [
  "len", "str", "int", "float", "bool", "list", "dict",
  "min", "max", "sum", "abs", "round", "sorted",
];

export function registerExpressionCompletion(monaco: Monaco, languageId: string): void {
  if (_completionRegistered) return;
  _completionRegistered = true;

  monaco.languages.registerCompletionItemProvider(languageId, {
    triggerCharacters: ["{", " ", ".", "[", '"', "'"],
    provideCompletionItems(model: ITextModel, position: IPosition) {
      const ctx = contextRegistry.get(model.uri.toString());
      if (!ctx) return { suggestions: [] };

      const lineUntilCursor = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      });

      // Suggest only when the cursor is *inside* a `{{ ... }}` block.
      if (!isInsideExpression(lineUntilCursor, model, position)) {
        return { suggestions: [] };
      }

      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endLineNumber: position.lineNumber,
        endColumn: word.endColumn,
      };

      // ── Match progressively narrower paths ──
      // nodes["LABEL"][0].<field>
      const nodesIndexed = lineUntilCursor.match(
        /nodes\[\s*["']([^"']+)["']\s*\]\[\s*\d+\s*\]\.[\w]*$/,
      );
      if (nodesIndexed) {
        return suggestNodeFields(monaco, ctx.schema.upstream, nodesIndexed[1], range);
      }

      // nodes["LABEL"]<cursor>  (or just after closing quote without bracket yet)
      const nodesLabel = lineUntilCursor.match(/nodes\[\s*["']([^"']*)$/);
      if (nodesLabel) {
        return suggestNodeLabels(monaco, ctx.schema.upstream, range);
      }

      // json.<field> or item.<field>
      const jsonField = lineUntilCursor.match(/(?:json|item)\.[\w]*$/);
      if (jsonField) {
        return suggestCurrentItemFields(monaco, ctx.schema.currentItem, range);
      }

      // items[0].<field>
      const itemsField = lineUntilCursor.match(/items\[\s*\d+\s*\]\.[\w]*$/);
      if (itemsField) {
        return suggestCurrentItemFields(monaco, ctx.schema.currentItem, range);
      }

      // vars.<field>
      const varsField = lineUntilCursor.match(/vars\.[\w]*$/);
      if (varsField) {
        // We don't track vars schema yet — Phase 3-Polish.
        return { suggestions: [] };
      }

      // Default: top-level identifiers
      return suggestTopLevel(monaco, range);
    },
  });
}

// ── Suggestion builders ─────────────────────────────────────────────────────

function suggestTopLevel(monaco: Monaco, range: monaco.IRange) {
  const suggestions = [
    ...TOP_LEVEL_NAMES.map((s) => ({
      label: s.label,
      kind: monaco.languages.CompletionItemKind.Variable,
      insertText: s.insertText,
      detail: s.detail,
      range,
    })),
    ...BUILTIN_FUNCTIONS.map((name) => ({
      label: name,
      kind: monaco.languages.CompletionItemKind.Function,
      insertText: `${name}($0)`,
      insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
      detail: "builtin",
      range,
    })),
  ];
  return { suggestions };
}

function suggestNodeLabels(
  monaco: Monaco,
  upstream: UpstreamNodeSchema[],
  range: monaco.IRange,
) {
  if (upstream.length === 0) {
    return {
      suggestions: [
        {
          label: "(no upstream nodes)",
          kind: monaco.languages.CompletionItemKind.Text,
          insertText: "",
          detail: "Connect nodes upstream to see suggestions",
          range,
        },
      ],
    };
  }
  return {
    suggestions: upstream.map((u) => ({
      label: u.label,
      kind: monaco.languages.CompletionItemKind.Module,
      // Insert the label and close the bracket+index, leaving cursor at .
      insertText: `${u.label}"][0].`,
      detail: u.nodeType,
      range,
    })),
  };
}

function suggestNodeFields(
  monaco: Monaco,
  upstream: UpstreamNodeSchema[],
  nodeLabel: string,
  range: monaco.IRange,
) {
  const target = upstream.find((u) => u.label === nodeLabel);
  if (!target || target.fields.length === 0) {
    return { suggestions: [] };
  }
  return {
    suggestions: target.fields.map((f) => ({
      label: f.name,
      kind: monaco.languages.CompletionItemKind.Field,
      insertText: f.name,
      detail: `${f.type}${typeof f.sampleValue === "string" ? `  · "${truncate(f.sampleValue, 40)}"` : ""}`,
      range,
    })),
  };
}

function suggestCurrentItemFields(
  monaco: Monaco,
  fields: ExpressionSchema["currentItem"],
  range: monaco.IRange,
) {
  if (fields.length === 0) {
    return {
      suggestions: [
        {
          label: "(run workflow to populate fields)",
          kind: monaco.languages.CompletionItemKind.Text,
          insertText: "",
          detail: "No upstream output sample available yet",
          range,
        },
      ],
    };
  }
  return {
    suggestions: fields.map((f) => ({
      label: f.name,
      kind: monaco.languages.CompletionItemKind.Field,
      insertText: f.name,
      detail: f.type,
      range,
    })),
  };
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function isInsideExpression(
  lineUntilCursor: string,
  model: { getValue: () => string; getOffsetAt: (p: { lineNumber: number; column: number }) => number },
  position: { lineNumber: number; column: number },
): boolean {
  // Cheap line-local heuristic first — covers single-line fields completely.
  const lastOpen = lineUntilCursor.lastIndexOf("{{");
  const lastClose = lineUntilCursor.lastIndexOf("}}");
  if (lastOpen > lastClose) return true;
  if (lastOpen !== -1 && lastClose === -1) return true;

  // Multi-line fall-back: scan backward through the full document.
  const offset = model.getOffsetAt(position);
  const text = model.getValue().slice(0, offset);
  const open = text.lastIndexOf("{{");
  const close = text.lastIndexOf("}}");
  return open > close;
}

function truncate(value: unknown, max: number): string {
  const s = String(value);
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

// Local Monaco type aliases — `monaco` namespace is only available at runtime.
declare namespace monaco {
  type IRange = {
    startLineNumber: number;
    startColumn: number;
    endLineNumber: number;
    endColumn: number;
  };
}
