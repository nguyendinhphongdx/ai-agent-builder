"use client";

import { memo, createElement } from "react";
import type { NodeProps } from "@xyflow/react";
import { getNodeEntry } from "../../nodes/registry";
import type { NodeData } from "../../nodes/types";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";
import { BaseNode } from "./BaseNode";

function CustomNodeComponent({ id, data, selected }: NodeProps) {
  const nodeData = data as unknown as NodeData;
  const entry = getNodeEntry(nodeData.nodeType);
  const runStatus = useWorkflowEditorStore((s) => s.nodeStatuses[id]);
  const isPinned = Array.isArray(
    (nodeData.config as { _pinned_output?: unknown } | undefined)?._pinned_output,
  );
  if (!entry) return null;

  // Annotation-style nodes (sticky notes) render their own layout — no shell,
  // no handles, no run-status badges. They have empty handles.{inputs,outputs}
  // so the runner never reaches them.
  if (entry.definition.handles.inputs.length === 0 && entry.definition.handles.outputs.length === 0) {
    return createElement(entry.node, {
      id,
      data: nodeData,
      // @ts-expect-error — node-content components opt into `selected` ad hoc
      selected,
    });
  }

  const isDisabled =
    (nodeData.config as { disabled?: unknown } | undefined)?.disabled === true;

  return (
    <div className={isDisabled ? "opacity-50 [&_*]:!border-dashed" : undefined}>
      <BaseNode
        nodeId={id}
        definition={entry.definition}
        label={nodeData.label}
        selected={selected}
        customHandles={nodeData._customHandles}
        runStatus={runStatus}
        isPinned={isPinned}
      >
        {createElement(entry.node, { id, data: nodeData })}
      </BaseNode>
    </div>
  );
}

export const CustomNode = memo(CustomNodeComponent);
