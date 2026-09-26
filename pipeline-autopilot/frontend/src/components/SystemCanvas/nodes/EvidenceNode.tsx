/**
 * EvidenceNode — small card representing a travelling evidence artifact.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 12: animated evidence particle card.
 */

import type { NodeProps } from '@xyflow/react';

export interface EvidenceNodeData {
  label: string;
  evidenceType?: string;
  [key: string]: unknown;
}

export function EvidenceNode({ data }: NodeProps) {
  const nodeData = data as EvidenceNodeData;
  return (
    <div
      style={{
        padding: '6px 12px',
        borderRadius: 4,
        background: '#1a2a3a',
        border: '1px solid #3b82d4',
        color: '#90caf9',
        fontSize: 11,
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      {nodeData.label ?? 'Evidence'}
    </div>
  );
}
