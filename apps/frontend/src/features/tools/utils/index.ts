import type { JsonSchema } from "../types";

/**
 * Extract {variable} template variables from a string.
 */
export function extractVariables(text: string): string[] {
  const vars = new Set<string>();
  for (const match of text.matchAll(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g)) {
    vars.add(match[1]);
  }
  return Array.from(vars);
}

/**
 * Extract all template variables from a config object (via JSON serialization).
 */
export function extractConfigVariables(config: Record<string, unknown>): string[] {
  return extractVariables(JSON.stringify(config));
}

/**
 * Build a JSON input schema from a list of variable names and optional descriptions.
 */
export function buildInputSchema(
  variables: string[],
  descriptions: Record<string, string> = {}
): JsonSchema {
  const properties: Record<string, { type: string; description?: string }> = {};
  for (const v of variables) {
    properties[v] = {
      type: "string",
      ...(descriptions[v] ? { description: descriptions[v] } : {}),
    };
  }
  return {
    type: "object",
    properties,
    required: variables,
  };
}

/**
 * Convert a key-value pair array to a plain object (for serialization).
 * Disabled rows are skipped.
 */
export interface KVPair {
  id: string;
  key: string;
  value: string;
  enabled: boolean;
}

export function kvsToObject(kvs: KVPair[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (const kv of kvs) {
    if (kv.enabled && kv.key.trim()) {
      result[kv.key.trim()] = kv.value;
    }
  }
  return result;
}

export function objectToKvs(obj: Record<string, string> | undefined): KVPair[] {
  if (!obj) return [];
  return Object.entries(obj).map(([key, value], i) => ({
    id: String(i),
    key,
    value,
    enabled: true,
  }));
}

let kvCounter = 0;
export function newKvId() {
  return `kv-${Date.now()}-${kvCounter++}`;
}
