/**
 * AnimatedEdge — base placeholder for animated edge types.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: full FailureEdge, EvidenceEdge, HealthyEdge implementation.
 */

import { BaseEdge, getStraightPath, type EdgeProps } from '@xyflow/react';

export function AnimatedEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  style,
  markerEnd,
}: EdgeProps) {
  const [edgePath] = getStraightPath({ sourceX, sourceY, targetX, targetY });
  return (
    <BaseEdge
      path={edgePath}
      markerEnd={markerEnd}
      style={{ stroke: '#2a2a4a', strokeWidth: 1.5, ...style }}
    />
  );
}
