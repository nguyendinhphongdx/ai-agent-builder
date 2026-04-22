"use client";

import { SourceHandle, TargetHandle, SubHandle } from "../handles";
import type { NodeTypeDefinition } from "../../nodes/types";
import { NodeConnectionTypes } from "../../nodes/types";

interface NodeHandlesProps {
  nodeId: string;
  definition: NodeTypeDefinition;
  /** Hide output handles (node renders its own, e.g. condition branches) */
  customOutputs?: boolean;
}

/**
 * Handle layout for a node:
 * - `main` inputs  → TargetHandle on left
 * - `main` outputs → SourceHandle on right (unless customOutputs is true)
 * - non-main inputs (ai_*) → SubHandle diamonds at the bottom
 */
export function NodeHandles({ nodeId, definition, customOutputs }: NodeHandlesProps) {
  const mainInputs = definition.handles.inputs.filter(
    (p) => p.type === NodeConnectionTypes.Main,
  );
  const subInputs = definition.handles.inputs.filter(
    (p) => p.type !== NodeConnectionTypes.Main,
  );
  const mainOutputs = definition.handles.outputs.filter(
    (p) => p.type === NodeConnectionTypes.Main,
  );

  return (
    <>
      {mainInputs.map((port) => (
        <TargetHandle key={port.id} handleId={port.id} label={port.label} />
      ))}

      {!customOutputs &&
        mainOutputs.map((port) => (
          <SourceHandle
            key={port.id}
            handleId={port.id}
            nodeId={nodeId}
            label={port.label}
          />
        ))}

      {subInputs.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 flex items-start justify-center gap-4">
          {subInputs.map((port) => (
            <SubHandle
              key={port.id}
              handleId={port.id}
              nodeId={nodeId}
              label={port.label ?? port.id}
              required={port.required}
            />
          ))}
        </div>
      )}
    </>
  );
}
