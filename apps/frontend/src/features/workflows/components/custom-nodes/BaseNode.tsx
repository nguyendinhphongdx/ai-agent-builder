"use client";

import type { ReactNode } from "react";
import type { NodeTypeDefinition } from "../../nodes/types";
import type { NodeRunStatus } from "../../stores/workflowEditorStore";
import { NodeShell } from "./NodeShell";
import { NodeBody } from "./NodeBody";
import { NodeHandles } from "./NodeHandles";

interface BaseNodeProps {
  nodeId: string;
  definition: NodeTypeDefinition;
  label?: string;
  selected?: boolean;
  customHandles?: boolean;
  runStatus?: NodeRunStatus;
  children?: ReactNode;
}

/**
 * Default node composition: Shell + Handles + Body.
 * Nodes with special layouts (condition branches, etc.) can compose
 * Shell/Handles/Body directly instead of using BaseNode.
 */
export function BaseNode({
  nodeId,
  definition,
  label,
  selected,
  customHandles,
  runStatus,
  children,
}: BaseNodeProps) {
  return (
    <div className="relative">
      <NodeShell shape={definition.shape} selected={selected} runStatus={runStatus}>
        <NodeBody
          icon={definition.icon}
          color={definition.color}
          label={label || definition.label}
          sublabel={definition.type}
          runStatus={runStatus}
        />
        <NodeHandles nodeId={nodeId} definition={definition} customOutputs={customHandles} />
      </NodeShell>

      {/* Per-node extra content (condition branches, etc.) */}
      {children && (
        <div className="absolute top-full left-0 right-0 mt-1">{children}</div>
      )}
    </div>
  );
}
