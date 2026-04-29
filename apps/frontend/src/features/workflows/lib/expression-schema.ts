/**
 * Schema introspection for ExpressionInput autocomplete.
 *
 * Walks upstream from a target node and pulls field names off the latest run's
 * recorded items — no new backend endpoint required, the data already lives in
 * the runs cache.
 */
import type { Node, Edge } from "@xyflow/react";
import type { WorkflowRun } from "../types";

export interface FieldSchema {
  name: string;
  type: "string" | "number" | "boolean" | "object" | "array" | "null";
  sampleValue?: unknown;
}

export interface UpstreamNodeSchema {
  /** Node label (preferred) or id used as the key in `nodes["..."]`. */
  key: string;
  /** The actual graph node id — useful for direct-parent checks. */
  nodeId: string;
  label: string;
  nodeType: string;
  fields: FieldSchema[];
}

export interface ExpressionSchema {
  /** Schema for the *current* node's input — i.e. what `json` / `item` resolve to. */
  currentItem: FieldSchema[];
  /** All ancestors reachable through edges, deduped by key. */
  upstream: UpstreamNodeSchema[];
  /** Pinned outputs on upstream nodes (works even before the workflow has ever run). */
  hasPinned: boolean;
}

/** Build a complete schema view for the node identified by `nodeId`. */
export function buildExpressionSchema(
  nodeId: string,
  nodes: Node[],
  edges: Edge[],
  latestRun: WorkflowRun | null,
): ExpressionSchema {
  const upstream = collectUpstream(nodeId, nodes, edges, latestRun);
  // `json` / `item` is the *immediate* input, so currentItem fields come from
  // direct predecessors only. Indirect ancestors are still suggested via
  // `nodes["X"]`. (Suggesting grandparent fields on `json.` would mislead —
  // those aren't passed through unless the predecessor explicitly forwards.)
  const directParentIds = new Set(
    edges.filter((e) => e.target === nodeId).map((e) => e.source),
  );
  const currentItem = mergeFields(
    upstream.filter((u) => directParentIds.has(u.nodeId)).flatMap((u) => u.fields),
  );
  const hasPinned = upstream.some((u) => u.fields.length > 0);
  return { currentItem, upstream, hasPinned };
}

/** Walk reverse graph from nodeId, collect schema for every reachable ancestor. */
function collectUpstream(
  nodeId: string,
  nodes: Node[],
  edges: Edge[],
  latestRun: WorkflowRun | null,
): UpstreamNodeSchema[] {
  const reverseAdj = buildReverseAdjacency(edges);
  const seen = new Set<string>();
  const out: UpstreamNodeSchema[] = [];

  const queue = [...(reverseAdj.get(nodeId) ?? [])];
  while (queue.length > 0) {
    const id = queue.shift()!;
    if (seen.has(id)) continue;
    seen.add(id);

    const node = nodes.find((n) => n.id === id);
    if (!node) continue;

    out.push(buildSingleUpstream(node, latestRun));

    for (const parent of reverseAdj.get(id) ?? []) queue.push(parent);
  }

  return out;
}

function buildSingleUpstream(
  node: Node,
  latestRun: WorkflowRun | null,
): UpstreamNodeSchema {
  const data = node.data as { nodeType?: string; label?: string; config?: { _pinned_output?: unknown } };
  const label = data.label || node.id;
  const nodeType = data.nodeType ?? "";

  // Prefer pinned output (frozen, always-available) over run output.
  const pinned = data.config?._pinned_output;
  let sample: Record<string, unknown> | null = null;
  if (Array.isArray(pinned) && pinned.length > 0) {
    sample = pinned[0] as Record<string, unknown>;
  } else if (latestRun) {
    const exec = latestRun.node_executions.find((e) => e.node_id === node.id);
    if (exec?.output_items?.length) {
      sample = exec.output_items[0];
    }
  }

  return {
    key: label,
    nodeId: node.id,
    label,
    nodeType,
    fields: sample ? extractFields(sample) : [],
  };
}

function extractFields(sample: Record<string, unknown>): FieldSchema[] {
  return Object.entries(sample).map(([name, value]) => ({
    name,
    type: detectType(value),
    sampleValue: value,
  }));
}

function detectType(value: unknown): FieldSchema["type"] {
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value)) return "array";
  if (typeof value === "object") return "object";
  if (typeof value === "string") return "string";
  if (typeof value === "number") return "number";
  if (typeof value === "boolean") return "boolean";
  return "null";
}

function buildReverseAdjacency(edges: Edge[]): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const edge of edges) {
    if (!map.has(edge.target)) map.set(edge.target, []);
    map.get(edge.target)!.push(edge.source);
  }
  return map;
}

/** Merge same-named fields, preferring the most-recently-seen sample. */
function mergeFields(fields: FieldSchema[]): FieldSchema[] {
  const dedup = new Map<string, FieldSchema>();
  for (const f of fields) dedup.set(f.name, f);
  return [...dedup.values()];
}
