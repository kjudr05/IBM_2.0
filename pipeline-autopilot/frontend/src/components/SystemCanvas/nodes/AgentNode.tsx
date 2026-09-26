/**
 * AgentNode — represents an investigation agent (hexagon shape).
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: full hexagon with active/idle states and agent name.
 *
 * Shape: CSS-clip-path hexagon (no SVG dependency, no extra lib).
 * Active state: bright blue border + glow, shown during AGENTS_ACTIVATING /
 *   EVIDENCE_FLOWING when this agent's evidence has arrived or is pending.
 * Idle state: muted dark with subtle border.
 */

import { Handle, Position, type NodeProps } from '@xyflow/react';
import { usePipelineStore } from '../../../state/pipelineStore';

// ---------------------------------------------------------------------------
// Data shape
// ---------------------------------------------------------------------------

export interface AgentNodeData {
  label: string;
  agentId?: string;
  /** Explicit override — if omitted, derived from store */
  active?: boolean;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Agent label → short display name
// ---------------------------------------------------------------------------

const AGENT_DISPLAY: Record<string, string> = {
  log_investigator:        'Logs',
  code_investigator:       'Code',
  dependency_investigator: 'Deps',
  test_investigator:       'Tests',
  infra_investigator:      'Infra',
  history_investigator:    'History',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AgentNode({ data, selected }: NodeProps) {
  const nodeData = data as AgentNodeData;
  const evidenceByAgent = usePipelineStore((s) => s.evidenceByAgent);
  const storyState = usePipelineStore((s) => s.storyState);

  const agentId = nodeData.agentId ?? '';

  // Derive active state:
  //   - explicit prop takes priority
  //   - otherwise: active if evidence has arrived for this agent, OR
  //     story is in AGENTS_ACTIVATING/EVIDENCE_FLOWING/EVIDENCE_CONVERGING
  const hasEvidence = agentId ? agentId in evidenceByAgent : false;
  const investigatingStates = new Set([
    'AGENTS_ACTIVATING',
    'EVIDENCE_FLOWING',
    'EVIDENCE_CONVERGING',
  ]);
  const isActive =
    nodeData.active !== undefined
      ? nodeData.active
      : hasEvidence || investigatingStates.has(storyState);

  // Colour palette
  const borderColour = isActive ? '#3b82d4' : '#2a3050';
  const bgColour     = isActive ? '#0f1e3a' : '#0c0c20';
  const labelColour  = isActive ? '#93c5fd' : '#57606a';
  const dotColour    = isActive ? '#3b82d4' : '#2a3050';

  const displayName =
    nodeData.label ??
    (agentId ? (AGENT_DISPLAY[agentId] ?? agentId) : 'Agent');

  return (
    <>
      <style>{`
        @keyframes an-glow {
          0%, 100% { filter: drop-shadow(0 0 0px rgba(59,130,212,0)); }
          50%       { filter: drop-shadow(0 0 6px rgba(59,130,212,0.8)); }
        }
        .an-active { animation: an-glow 1.4s ease-in-out infinite; }
      `}</style>

      <Handle type="target" position={Position.Left}   style={{ background: borderColour }} />
      <Handle type="source" position={Position.Right}  style={{ background: borderColour }} />
      <Handle type="target" position={Position.Top}    style={{ background: borderColour }} />
      <Handle type="source" position={Position.Bottom} style={{ background: borderColour }} />

      {/*
       * Hexagon shape via clip-path.
       * The outer wrapper sets the clip; inner div holds the content.
       * We layer a border-simulation by making the outer div slightly larger
       * and the same clip, coloured with the border colour.
       */}
      <div
        data-testid="agent-node"
        data-active={String(isActive)}
        data-agent-id={agentId || undefined}
        className={isActive ? 'an-active' : undefined}
        style={{
          // Hexagon clip
          clipPath: 'polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)',
          background: selected ? '#1e3060' : bgColour,
          border: 'none',
          width: 100,
          height: 88,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'default',
          userSelect: 'none',
          outline: `3px solid ${selected ? '#60a5fa' : borderColour}`,
          outlineOffset: -3,
          transition: 'background 0.3s, outline-color 0.3s',
        }}
      >
        {/* Status dot */}
        <span
          data-testid="agent-dot"
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: dotColour,
            display: 'block',
            marginBottom: 4,
            transition: 'background 0.3s',
          }}
        />

        {/* Agent name */}
        <span
          data-testid="agent-label"
          style={{
            fontSize: 11,
            fontWeight: 600,
            fontFamily: 'system-ui, sans-serif',
            color: labelColour,
            textAlign: 'center',
            lineHeight: 1.2,
            padding: '0 8px',
            transition: 'color 0.3s',
          }}
        >
          {displayName}
        </span>
      </div>
    </>
  );
}
