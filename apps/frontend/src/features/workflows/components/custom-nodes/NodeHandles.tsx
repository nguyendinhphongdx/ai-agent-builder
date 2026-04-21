"use client";

import { SourceHandle, TargetHandle, SubHandle } from "../handles";
import type { NodeTypeDefinition } from "../../nodes/types";

interface NodeHandlesProps {
  nodeId: string;
  definition: NodeTypeDefinition;
  /** Hide output handles (node renders its own, e.g. condition branches) */
  customOutputs?: boolean;
}

/**
 * Handle layout for a node: inputs on left, outputs on right, sub-connections on bottom.
 * Handles are rendered as children of the node shell (React Flow wraps the whole node in its
 * own positioning wrapper; Handle components use absolute positioning internally).
 */
export function NodeHandles({ nodeId, definition, customOutputs }: NodeHandlesProps) {
  const hasSubs = definition.subConnections && definition.subConnections.length > 0;

  return (
    <>
      {definition.handles.inputs.map((port) => (
        <TargetHandle key={port.id} handleId={port.id} label={port.label} />
      ))}

      {!customOutputs &&
        definition.handles.outputs.map((port) => (
          <SourceHandle
            key={port.id}
            handleId={port.id}
            nodeId={nodeId}
            label={port.label}
          />
        ))}

      {hasSubs && (
        <div className="absolute top-full left-0 right-0 mt-1 flex items-start justify-center gap-4">
          {definition.subConnections!.map((sub) => (
            <SubHandle
              key={sub.id}
              handleId={`sub_${sub.id}`}
              nodeId={nodeId}
              label={sub.label}
              required={sub.required}
            />
          ))}
        </div>
      )}
    </>
  );
}
