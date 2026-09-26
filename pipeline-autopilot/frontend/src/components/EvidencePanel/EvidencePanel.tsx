/**
 * EvidencePanel — sliding panel for Level 2 (causal) and Level 3 (technical) disclosure.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 13: full progressive-disclosure implementation.
 */

import { usePipelineStore } from '../../state/pipelineStore';

export function EvidencePanel() {
  const causalChain = usePipelineStore((s) => s.causalChain);

  if (!causalChain) return null;

  return (
    <aside
      style={{
        width: 320,
        height: '100%',
        background: '#13131f',
        borderLeft: '1px solid #2a2a4a',
        padding: 16,
        color: '#c9d1d9',
        fontFamily: 'system-ui, sans-serif',
        fontSize: 13,
        overflowY: 'auto',
      }}
    >
      <h3 style={{ margin: '0 0 12px', color: '#90caf9', fontSize: 14 }}>
        Causal Chain
      </h3>
      <p style={{ margin: 0, color: '#8b949e', lineHeight: 1.6 }}>
        {causalChain.narrative}
      </p>
      {/* Task 13: CausalChain + EvidenceCard + TechnicalDrill */}
    </aside>
  );
}
