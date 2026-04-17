"use client";

import { Handle, Position } from "@xyflow/react";

interface TargetHandleProps {
  handleId: string;
  label?: string;
}

export function TargetHandle({ handleId, label }: TargetHandleProps) {
  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        id={handleId}
        className="w-2.5! h-2.5! bg-muted-foreground/40! border-2! border-background!"
      />
      {label && (
        <span className="absolute left-5 top-1/2 -translate-y-1/2 text-[9px] font-medium text-muted-foreground whitespace-nowrap">
          {label}
        </span>
      )}
    </>
  );
}
