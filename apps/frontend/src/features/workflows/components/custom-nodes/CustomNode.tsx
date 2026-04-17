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
  if (!entry) return null;

  return (
    <BaseNode
      nodeId={id}
      definition={entry.definition}
      label={nodeData.label}
      selected={selected}
      customHandles={nodeData._customHandles}
      runStatus={runStatus}
    >
      {createElement(entry.node, { id, data: nodeData })}
    </BaseNode>
  );
}

export const CustomNode = memo(CustomNodeComponent);
