/**
 * RecoveryReport — final summary card shown after successful validation.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 15: full recovery report card with root cause, fix, and validation result.
 */

import { usePipelineStore } from '../../state/pipelineStore';

export function RecoveryReport() {
  const report = usePipelineStore((s) => s.recoveryReport);

  if (!report) return null;

  return (
    <div
      style={{
        padding: '16px 20px',
        background: '#13131f',
        border: '1px solid #2a4a2a',
        borderRadius: 8,
        color: '#c9d1d9',
        fontFamily: 'system-ui, sans-serif',
        fontSize: 13,
      }}
    >
      <h3 style={{ margin: '0 0 8px', color: '#4ade80', fontSize: 14 }}>
        Recovery Complete
      </h3>
      <p style={{ margin: 0, lineHeight: 1.6, color: '#8b949e' }}>
        {report.root_cause_summary}
      </p>
      {/* Task 15: full report card */}
    </div>
  );
}
