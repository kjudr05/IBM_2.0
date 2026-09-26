/**
 * ServiceNode — represents a service in the software system.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: full implementation with health ring, icon, and status colours.
 */

import type { NodeProps } from '@xyflow/react';

export interface ServiceNodeData {
  label: string;
  health?: 'HEALTHY' | 'DEGRADED' | 'FAILED';
  [key: string]: unknown;
}

export function ServiceNode({ data }: NodeProps) {
  const nodeData = data as ServiceNodeData;
  return (
    <div
      style={{
        padding: '10px 16px',
        borderRadius: 8,
        background: '#1a1a2e',
        border: '1px solid #2a2a4a',
        color: '#c9d1d9',
        fontSize: 13,
        fontFamily: 'system-ui, sans-serif',
        minWidth: 120,
        textAlign: 'center',
      }}
    >
      {nodeData.label ?? 'Service'}
    </div>
  );
}
