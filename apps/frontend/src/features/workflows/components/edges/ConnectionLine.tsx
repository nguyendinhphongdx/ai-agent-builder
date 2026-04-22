"use client";

import { getBezierPath, type ConnectionLineComponentProps } from "@xyflow/react";

export function ConnectionLine({
  fromX,
  fromY,
  toX,
  toY,
  fromPosition,
  toPosition,
}: ConnectionLineComponentProps) {
  const [edgePath] = getBezierPath({
    sourceX: fromX,
    sourceY: fromY,
    targetX: toX,
    targetY: toY,
    sourcePosition: fromPosition,
    targetPosition: toPosition,
    curvature: 0.3,
  });

  return (
    <g>
      <path
        d={edgePath}
        fill="none"
        stroke="var(--primary)"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeDasharray="6 4"
      />
      <circle
        cx={toX}
        cy={toY}
        r={4}
        fill="var(--primary)"
        stroke="var(--background)"
        strokeWidth={2}
      />
    </g>
  );
}
