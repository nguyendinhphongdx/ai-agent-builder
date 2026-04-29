/**
 * Resolve input items for a node — used by "Execute step" in NDV.
 *
 * Tries, in order:
 *   1. The node's own recorded input_items from the latest run
 *   2. Concatenated output_items from upstream nodes (latest run)
 *   3. Concatenated `_pinned_output` from upstream node configs
 *
 * Returns `{ items: [], source: "empty" }` when nothing is available — the
 * caller decides whether to disable the button or run with empty input.
 */
import type { Node, Edge } from "@xyflow/react";
import type { WorkflowRun } from "../types";

export type InputSource = "exec" | "upstream" | "pinned" | "empty";

export interface ResolvedInput {
  items: Record<string, unknown>[];
  source: InputSource;
}

export function resolveNodeInput(
  run: WorkflowRun | null,
  nodeId: string,
  nodes: Node[],
  edges: Edge[],
): ResolvedInput {
  // 1. Direct from the node's own execution record on the latest run.
  const currentExec = run?.node_executions.find((e) => e.node_id === nodeId);
  if (currentExec?.input_items?.length) {
    return { items: currentExec.input_items, source: "exec" };
  }

  const incomingEdges = edges.filter((e) => e.target === nodeId);

  // 2. Upstream output from the latest run.
  if (run && incomingEdges.length > 0) {
    const items: Record<string, unknown>[] = [];
    for (const edge of incomingEdges) {
      const upstream = run.node_executions.find((e) => e.node_id === edge.source);
      if (upstream?.output_items) items.push(...upstream.output_items);
    }
    if (items.length) return { items, source: "upstream" };
  }

  // 3. Upstream pinned data (works even before the workflow has ever run).
  const pinned: Record<string, unknown>[] = [];
  for (const edge of incomingEdges) {
    const source = nodes.find((n) => n.id === edge.source);
    const pinnedOutput = (source?.data as { config?: { _pinned_output?: unknown } })
      ?.config?._pinned_output;
    if (Array.isArray(pinnedOutput)) {
      pinned.push(...(pinnedOutput as Record<string, unknown>[]));
    }
  }
  if (pinned.length) return { items: pinned, source: "pinned" };

  return { items: [], source: "empty" };
}
