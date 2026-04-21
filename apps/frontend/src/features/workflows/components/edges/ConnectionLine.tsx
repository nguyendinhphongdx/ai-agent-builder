"use client";

import { type ConnectionLineComponentProps } from "@xyflow/react";

import React from 'react';
import { getStraightPath } from '@xyflow/react';

export function ConnectionLine({ fromX, fromY, toX, toY, connectionLineStyle }: ConnectionLineComponentProps) {
  const [edgePath] = getStraightPath({
    sourceX: fromX,
    sourceY: fromY,
    targetX: toX,
    targetY: toY,
  });
 
  return (
    <g>
      <path style={connectionLineStyle} fill="none" d={edgePath} />
    </g>
  );
}