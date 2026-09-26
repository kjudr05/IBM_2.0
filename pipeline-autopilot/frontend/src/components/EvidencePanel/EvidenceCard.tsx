/**
 * EvidenceCard — shows one evidence artifact summary with confidence bar.
 *
 * Task 13: full card with confidence bar, type badge, and summary text.
 *
 * Shows a summary of a single evidence artifact. The card is intentionally
 * compact — detailed inspection is handled by TechnicalDrill.
 */

import type { AnyEvidence } from '../../types/evidence';

// ---------------------------------------------------------------------------
// Type → display metadata
// ---------------------------------------------------------------------------

const EVIDENCE_TYPE_COLOUR: Record<string, string> = {
  failure:    '#ef4444',
  change:     '#3b82f6',
  dependency: '#a855f7',
  test:       '#eab308',
  infra:      '#f97316',
  historical: '#22c55e',
};

const EVIDENCE_TYPE_LABEL: Record<string, string> = {
  failure:    'Failure Log',
  change:     'Code Change',
  dependency: 'Dependency',
  test:       'Test Results',
  infra:      'Infrastructure',
  historical: 'Historical',
};

const EVIDENCE_TYPE_ICON: Record<string, string> = {
  failure:    '✕',
  change:     '⊙',
  dependency: '◈',
  test:       '◎',
  infra:      '⊞',
  historical: '◷',
};

// ---------------------------------------------------------------------------
// EvidenceCard — public export
// ---------------------------------------------------------------------------

export interface EvidenceCardProps {
  evidence: AnyEvidence;
  /** Called when the user clicks "Inspect" to open TechnicalDrill */
  onInspect?: (evidence: AnyEvidence) => void;
  /** Whether this card is the currently inspected one */
  active?: boolean;
}

export function EvidenceCard({ evidence, onInspect, active = false }: EvidenceCardProps) {
  const colour = EVIDENCE_TYPE_COLOUR[evidence.evidence_type] ?? '#8b949e';
  const typeLabel = EVIDENCE_TYPE_LABEL[evidence.evidence_type] ?? evidence.evidence_type;
  const icon = EVIDENCE_TYPE_ICON[evidence.evidence_type] ?? '◉';
  const confidencePct = Math.round(evidence.confidence * 100);

  return (
    <div
      data-testid={`evidence-card-${evidence.evidence_id}`}
      data-type={evidence.evidence_type}
      data-active={active ? 'true' : 'false'}
      style={{
        background: active ? `rgba(${hexToRgb(colour)},0.08)` : 'rgba(255,255,255,0.02)',
        border: `1px solid ${active ? colour : '#2a2a4a'}`,
        borderRadius: 7,
        padding: '9px 11px',
        cursor: onInspect ? 'pointer' : 'default',
        transition: 'border-color 0.15s, background 0.15s',
      }}
      onClick={() => onInspect?.(evidence)}
    >
      {/* Header row: icon + type badge + agent id */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
        <span style={{ fontSize: 11, color: colour }}>{icon}</span>
        <span
          data-testid={`ec-type-badge-${evidence.evidence_id}`}
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: colour,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}
        >
          {typeLabel}
        </span>
        <span style={{ fontSize: 10, color: '#57606a', marginLeft: 'auto' }}>
          {evidence.source.agent_id}
        </span>
      </div>

      {/* Summary text */}
      <div
        data-testid={`ec-summary-${evidence.evidence_id}`}
        style={{ fontSize: 11, color: '#c9d1d9', lineHeight: 1.5, marginBottom: 6 }}
      >
        {evidence.summary}
      </div>

      {/* Confidence bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div
          style={{
            flex: 1,
            height: 3,
            background: '#1e2030',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            data-testid={`ec-confidence-bar-${evidence.evidence_id}`}
            style={{
              width: `${confidencePct}%`,
              height: '100%',
              background: colour,
              borderRadius: 2,
            }}
          />
        </div>
        <span style={{ fontSize: 10, color: '#57606a', flexShrink: 0 }}>{confidencePct}%</span>
        {onInspect && (
          <button
            data-testid={`ec-inspect-btn-${evidence.evidence_id}`}
            style={{
              fontSize: 10,
              color: active ? colour : '#57606a',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '0 2px',
              textDecoration: 'underline',
              flexShrink: 0,
            }}
            onClick={(e) => {
              e.stopPropagation();
              onInspect(evidence);
            }}
          >
            {active ? 'Close' : 'Inspect'}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

/** Convert #rrggbb to "r,g,b" for rgba() usage */
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return '255,255,255';
  return `${parseInt(result[1], 16)},${parseInt(result[2], 16)},${parseInt(result[3], 16)}`;
}
