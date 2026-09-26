/**
 * AgentNode — represents an investigation agent (hexagon shape placeholder).
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: full hexagon with active/idle states and agent name.
 */

import type { NodeProps } from '@xyflow/react';

export interface AgentNodeData {
  label: string;
  agentId?: string;
  active?: boolean;
  [key: string]: unknown;
}

export function AgentNode({ data }: NodeProps) {
  const nodeData = data as AgentNodeData;
  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: 4,
        background: nodeData.active ? '#1e2d4a' : '#141428',
        border: `1px solid ${nodeData.active ? '#3b82d4' : '#2a2a4a'}`,
        color: '#c9d1d9',
        fontSize: 12,
        fontFamily: 'system-ui, sans-serif',
        minWidth: 100,
        textAlign: 'center',
      }}
    >
      {nodeData.label ?? 'Agent'}
    </div>
  );
}
