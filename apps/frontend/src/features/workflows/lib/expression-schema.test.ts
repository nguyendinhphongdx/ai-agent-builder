import { describe, expect, it } from "vitest";
import type { Edge, Node } from "@xyflow/react";
import { buildExpressionSchema } from "./expression-schema";
import type { WorkflowRun } from "../types";

function makeNode(id: string, label: string, nodeType = "llm"): Node {
  return {
    id,
    type: "baseNode",
    position: { x: 0, y: 0 },
    data: { nodeType, label, config: {} },
  } as unknown as Node;
}

function makeEdge(source: string, target: string): Edge {
  return { id: `${source}-${target}`, source, target } as Edge;
}

function fakeRun(executions: Array<{ node_id: string; output_items: any[] }>): WorkflowRun {
  return {
    id: "run-1",
    workflow_id: "wf-1",
    user_id: "u-1",
    conversation_id: null,
    status: "completed",
    is_partial: false,
    input_data: {},
    output_data: null,
    error_message: null,
    node_executions: executions.map((e) => ({
      node_id: e.node_id,
      node_type: "llm",
      label: null,
      status: "completed",
      input_items: [],
      output_items: e.output_items,
      error: null,
      started_at: null,
      completed_at: null,
      tokens_used: 0,
    })),
    total_tokens: 0,
    total_cost: 0,
    started_at: "",
    completed_at: null,
  };
}

describe("buildExpressionSchema", () => {
  it("currentItem includes ONLY direct parents, not grandparents", () => {
    // a → b → c. Current node is c. `json` should be b's output, not a's.
    const nodes = [makeNode("a", "A"), makeNode("b", "B"), makeNode("c", "C")];
    const edges = [makeEdge("a", "b"), makeEdge("b", "c")];
    const run = fakeRun([
      { node_id: "a", output_items: [{ from_a: 1 }] },
      { node_id: "b", output_items: [{ from_b: 2 }] },
    ]);

    const schema = buildExpressionSchema("c", nodes, edges, run);
    const fieldNames = schema.currentItem.map((f) => f.name);

    expect(fieldNames).toContain("from_b");
    expect(fieldNames).not.toContain("from_a");
  });

  it("upstream walks ancestors transitively for nodes['X'] suggestions", () => {
    const nodes = [makeNode("a", "A"), makeNode("b", "B"), makeNode("c", "C")];
    const edges = [makeEdge("a", "b"), makeEdge("b", "c")];
    const run = fakeRun([
      { node_id: "a", output_items: [{}] },
      { node_id: "b", output_items: [{}] },
    ]);

    const schema = buildExpressionSchema("c", nodes, edges, run);
    const upstreamLabels = schema.upstream.map((u) => u.label);

    expect(upstreamLabels).toEqual(expect.arrayContaining(["A", "B"]));
  });

  it("returns empty schema when no upstream + no run", () => {
    const schema = buildExpressionSchema("solo", [makeNode("solo", "Solo")], [], null);
    expect(schema.currentItem).toEqual([]);
    expect(schema.upstream).toEqual([]);
  });

  it("prefers pinned output over latest run", () => {
    const pinned = [{ pinned_field: "pinned-value" }];
    const node = makeNode("a", "A");
    (node.data as any).config = { _pinned_output: pinned };

    const nodes = [node, makeNode("b", "B")];
    const edges = [makeEdge("a", "b")];
    const run = fakeRun([{ node_id: "a", output_items: [{ run_field: "run-value" }] }]);

    const schema = buildExpressionSchema("b", nodes, edges, run);
    const fieldNames = schema.currentItem.map((f) => f.name);

    expect(fieldNames).toContain("pinned_field");
    expect(fieldNames).not.toContain("run_field");
  });
});
