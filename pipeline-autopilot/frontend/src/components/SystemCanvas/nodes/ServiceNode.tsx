/**
 * ServiceNode — represents a service in the software system.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: full implementation with health ring, icon, and status colours.
 *
 * Health states: HEALTHY (green) | DEGRADED (amber) | FAILED (red).
 * The outer ring and background tint reflect the current health state.
 * A React Flow Handle is placed on each side so edges can attach anywhere.
 */

import { Handle, Position, type NodeProps } from '@xyflow/react';
import { usePipelineStore } from '../../../state/pipelineStore';

// ---------------------------------------------------------------------------
// Data shape
// ---------------------------------------------------------------------------

export interface ServiceNodeData {
  label: string;
  health?: 'HEALTHY' | 'DEGRADED' | 'FAILED';
  /** Optional icon character / emoji rendered inside the node */
  icon?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Health palette
// ---------------------------------------------------------------------------

const HEALTH_COLOURS: Record<string, { ring: string; bg: string; text: string }> = {
  HEALTHY:  { ring: '#22c55e', bg: '#0f2e1a', text: '#4ade80' },
  DEGRADED: { ring: '#f59e0b', bg: '#2e1e00', text: '#fbbf24' },
  FAILED:   { ring: '#ef4444', bg: '#2e0f0f', text: '#f87171' },
};

const DEFAULT_COLOURS = { ring: '#3b82d4', bg: '#1a1a2e', text: '#93c5fd' };

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ServiceNode({ data, selected }: NodeProps) {
  const nodeData = data as ServiceNodeData;
  const storyState = usePipelineStore((s) => s.storyState);

  // Derive effective health from story state when not explicitly set:
  //   FAILURE_PROPAGATING → FAILED
  //   SYSTEM_RECOVERING   → DEGRADED (transitioning back)
  //   COMPLETE            → HEALTHY (recovered)
  const derivedHealth: ServiceNodeData['health'] =
    storyState === 'FAILURE_PROPAGATING' ? 'FAILED' :
    storyState === 'SYSTEM_RECOVERING'   ? 'DEGRADED' :
    'HEALTHY';

  const health = nodeData.health ?? derivedHealth;
  const colours = HEALTH_COLOURS[health] ?? DEFAULT_COLOURS;
  const isPulsing = health === 'FAILED' && storyState === 'FAILURE_PROPAGATING';

  return (
    <>
      {/* CSS keyframe injected once — safe in jsdom/vitest too */}
      <style>{`
        @keyframes sn-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.7); }
          50%       { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        }
        .sn-pulse { animation: sn-pulse 1.2s ease-in-out infinite; }
      `}</style>

      <Handle type="target" position={Position.Left}  style={{ background: colours.ring }} />
      <Handle type="target" position={Position.Top}   style={{ background: colours.ring }} />
      <Handle type="source" position={Position.Right} style={{ background: colours.ring }} />
      <Handle type="source" position={Position.Bottom} style={{ background: colours.ring }} />

      <div
        data-testid="service-node"
        data-health={health}
        className={isPulsing ? 'sn-pulse' : undefined}
        style={{
          padding: '10px 16px',
          borderRadius: 10,
          background: colours.bg,
          border: `2px solid ${selected ? '#60a5fa' : colours.ring}`,
          color: '#c9d1d9',
          fontSize: 13,
          fontFamily: 'system-ui, sans-serif',
          minWidth: 130,
          textAlign: 'center',
          transition: 'border-color 0.3s, background 0.3s',
          cursor: 'default',
          userSelect: 'none',
        }}
      >
        {/* Icon row */}
        {nodeData.icon && (
          <div style={{ fontSize: 18, marginBottom: 4, lineHeight: 1 }}>
            {nodeData.icon}
          </div>
        )}

        {/* Service label */}
        <div style={{ fontWeight: 600, marginBottom: 6 }}>
          {nodeData.label ?? 'Service'}
        </div>

        {/* Health ring / status pill */}
        <div
          data-testid="health-indicator"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            fontSize: 10,
            color: colours.text,
            background: 'rgba(0,0,0,0.3)',
            borderRadius: 12,
            padding: '2px 8px',
            border: `1px solid ${colours.ring}`,
          }}
        >
          {/* Status dot */}
          <span
            data-testid="health-dot"
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: colours.ring,
              display: 'inline-block',
              flexShrink: 0,
            }}
          />
          {health}
        </div>
      </div>
    </>
  );
}
