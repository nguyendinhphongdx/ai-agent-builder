import type { Connection, Edge, Node } from "@xyflow/react";
import { getNodeEntry } from "../nodes/registry";
import type { HandlePort } from "../nodes/types";

/**
 * Resolves the HandlePort config for a given node + handle id on the requested
 * direction. Returns `undefined` if the node or handle is not found.
 */
function resolvePort(
  node: Node | undefined,
  handleId: string | null | undefined,
  side: "inputs" | "outputs",
): HandlePort | undefined {
  if (!node) return undefined;
  const entry = getNodeEntry((node.data as { nodeType?: string }).nodeType ?? "");
  if (!entry) return undefined;
  const ports = entry.definition.handles[side];
  return ports.find((p) => p.id === handleId) ?? ports[0];
}

/**
 * Returns `true` when the connection is allowed, `false` otherwise.
 * Called by React Flow on every drag tick — keep it cheap.
 */
export function isValidConnection(
  connection: Connection | Edge,
  nodes: Node[],
  edges: Edge[],
): boolean {
  // 1. No self-loops
  if (connection.source === connection.target) return false;

  const src = nodes.find((n) => n.id === connection.source);
  const tgt = nodes.find((n) => n.id === connection.target);
  if (!src || !tgt) return false;

  const srcPort = resolvePort(src, connection.sourceHandle, "outputs");
  const tgtPort = resolvePort(tgt, connection.targetHandle, "inputs");
  if (!srcPort || !tgtPort) return false;

  // 2. Types must match
  if (srcPort.type !== tgtPort.type) return false;

  // 3. Apply target port's filter (constraining which source node types plug in)
  const f = tgtPort.filter;
  const srcType = (src.data as { nodeType?: string }).nodeType ?? "";
  if (f?.excludedNodes?.includes(srcType)) return false;
  if (f?.nodes && !f.nodes.includes(srcType)) return false;

  // 4. maxConnections on the target port
  if (tgtPort.maxConnections !== undefined) {
    const existing = edges.filter(
      (e) => e.target === connection.target && e.targetHandle === connection.targetHandle,
    ).length;
    if (existing >= tgtPort.maxConnections) return false;
  }

  return true;
}
