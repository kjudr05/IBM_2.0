/**
 * AnimatedEdge and specialised edge variants.
 *
 * Task 10: AnimatedEdge — minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: FailureEdge — red particle stream during FAILURE_PROPAGATING.
 *          EvidenceEdge — animated blue dot stream.
 *          HealthyEdge  — thin grey animated dash (default).
 *
 * All three variants are based on the same SVG path pattern to keep them
 * consistent and interchangeable in the edge type map.
 *
 * FailureEdge uses a CSS stroke-dasharray animation on the path itself plus
 * an SVG circle "particle" that traverses the path via animateMotion.
 * This works in both browser and jsdom (the circle just renders statically
 * in tests — no real animation API required).
 */

import {
  BaseEdge,
  getStraightPath,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';
import { usePipelineStore } from '../../../state/pipelineStore';

// ---------------------------------------------------------------------------
// Shared keyframe CSS (injected once at module level via a singleton pattern)
// ---------------------------------------------------------------------------

const EDGE_STYLES = `
@keyframes fe-dash {
  to { stroke-dashoffset: -20; }
}
@keyframes fe-pulse-opacity {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
@keyframes ee-dash {
  to { stroke-dashoffset: -16; }
}
`;

// ---------------------------------------------------------------------------
// AnimatedEdge — default thin grey animated dash (HealthyEdge behaviour)
// ---------------------------------------------------------------------------

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
    <>
      <style>{EDGE_STYLES}</style>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: '#2a2a4a',
          strokeWidth: 1.5,
          strokeDasharray: '6 4',
          animation: 'fe-dash 1s linear infinite',
          ...style,
        }}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// HealthyEdge — normal system data flow (thin grey animated dash)
// ---------------------------------------------------------------------------

export function HealthyEdge(props: EdgeProps) {
  return <AnimatedEdge {...props} />;
}

// ---------------------------------------------------------------------------
// FailureEdge — red particle stream, animates on FAILURE_PROPAGATING
// ---------------------------------------------------------------------------

export function FailureEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
}: EdgeProps) {
  const storyState = usePipelineStore((s) => s.storyState);
  const isActive = storyState === 'FAILURE_PROPAGATING';

  const [edgePath] = getStraightPath({ sourceX, sourceY, targetX, targetY });

  return (
    <>
      <style>{EDGE_STYLES}</style>

      {/* Base red path — always visible */}
      <path
        d={edgePath}
        data-testid="failure-edge-path"
        data-active={String(isActive)}
        fill="none"
        stroke={isActive ? '#ef4444' : '#6b2020'}
        strokeWidth={isActive ? 2.5 : 1.5}
        strokeDasharray={isActive ? '8 4' : '4 6'}
        style={{
          animation: isActive ? 'fe-dash 0.6s linear infinite' : 'none',
          opacity: isActive ? 1 : 0.5,
          transition: 'stroke 0.3s, stroke-width 0.3s, opacity 0.3s',
        }}
        markerEnd={markerEnd}
      />

      {/* Particle: SVG circle traversing the edge path when active */}
      {isActive && (
        <circle
          r={4}
          fill="#ef4444"
          data-testid="failure-particle"
          style={{ opacity: 0.9 }}
        >
          <animateMotion
            dur="0.8s"
            repeatCount="indefinite"
            rotate="auto"
          >
            <mpath href={`#fe-${sourceX}-${sourceY}`} />
          </animateMotion>
        </circle>
      )}

      {/* Named path for mpath reference — invisible */}
      {isActive && (
        <path
          id={`fe-${sourceX}-${sourceY}`}
          d={edgePath}
          fill="none"
          stroke="none"
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// EvidenceEdge — animated blue dot stream
// ---------------------------------------------------------------------------

export function EvidenceEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
}: EdgeProps) {
  const [edgePath] = getBezierPath({ sourceX, sourceY, targetX, targetY });

  return (
    <>
      <style>{EDGE_STYLES}</style>
      <path
        d={edgePath}
        data-testid="evidence-edge-path"
        fill="none"
        stroke="#3b82d4"
        strokeWidth={1.5}
        strokeDasharray="5 5"
        style={{ animation: 'ee-dash 0.8s linear infinite' }}
        markerEnd={markerEnd}
      />
    </>
  );
}
