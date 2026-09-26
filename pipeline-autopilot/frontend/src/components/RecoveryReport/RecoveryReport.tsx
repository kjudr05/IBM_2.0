/**
 * RecoveryReport — final summary card shown after successful validation.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 15: full recovery report card with root cause, fix, validation result,
 *          counterfactual outcome, and confidence display.
 * Polish: compact visual hierarchy — non-technical first, technical second.
 *
 * Visual hierarchy (top → bottom):
 *   1. RECOVERY COMPLETE + PASSED badge           ← instant recognition
 *   2. What Happened (plain language)             ← non-technical
 *   3. Root Cause label                           ← semi-technical
 *   4. Proposed Fix (description + rationale)     ← action
 *   5. Validation status + confidence bar         ← result
 *   6. Recovery count + causal explanation        ← outcome + detail
 */

import { usePipelineStore } from '../../state/pipelineStore';
import type { ValidationStatus, FixType } from '../../types/fix';

// ---------------------------------------------------------------------------
// Palette helpers — mirror app-wide conventions
// ---------------------------------------------------------------------------

const VALIDATION_PALETTE: Record<
  ValidationStatus,
  { bg: string; ring: string; text: string; label: string; dotColor: string }
> = {
  PASSED:  { bg: '#0f2e1a', ring: '#22c55e', text: '#4ade80', label: 'PASSED',  dotColor: '#22c55e' },
  PARTIAL: { bg: '#2e1e00', ring: '#f59e0b', text: '#fbbf24', label: 'PARTIAL', dotColor: '#f59e0b' },
  FAILED:  { bg: '#2e0f0f', ring: '#ef4444', text: '#f87171', label: 'FAILED',  dotColor: '#ef4444' },
};

const FIX_TYPE_LABEL: Record<FixType, string> = {
  DEPENDENCY_CHANGE: 'Dependency Update',
  CODE_PATCH:        'Code Patch',
  CONFIG_CHANGE:     'Configuration Change',
  ENV_FIX:           'Environment Fix',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Compact validation status badge */
function ValidationBadge({ status }: { status: ValidationStatus }) {
  const p = VALIDATION_PALETTE[status];
  return (
    <span
      data-testid="rr-validation-badge"
      data-status={status}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: p.text,
        background: p.bg,
        border: `1px solid ${p.ring}`,
        borderRadius: 10,
        padding: '2px 8px',
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: p.dotColor,
          flexShrink: 0,
          display: 'inline-block',
        }}
      />
      {p.label}
    </span>
  );
}

/** Slim horizontal confidence bar + percentage */
function ConfidenceBar({ value, color = '#3b82d4' }: { value: number; color?: string }) {
  const pct = Math.round(value * 100);
  return (
    <div
      data-testid="rr-confidence-bar"
      style={{ display: 'flex', alignItems: 'center', gap: 6 }}
    >
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
          style={{
            width: `${pct}%`,
            height: '100%',
            background: color,
            borderRadius: 2,
            transition: 'width 0.5s ease',
          }}
        />
      </div>
      <span
        data-testid="rr-confidence-pct"
        style={{ fontSize: 10, color: '#57606a', flexShrink: 0, minWidth: 30 }}
      >
        {pct}%
      </span>
    </div>
  );
}

/** Key-value row with uppercase label */
function Row({
  label,
  children,
  testId,
  accent,
}: {
  label: string;
  children: React.ReactNode;
  testId?: string;
  accent?: string;
}) {
  return (
    <div style={{ marginBottom: 8 }} data-testid={testId}>
      <div
        style={{
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: accent ?? '#57606a',
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 12, color: '#c9d1d9', lineHeight: 1.5 }}>{children}</div>
    </div>
  );
}

/** Thin section divider */
function Divider() {
  return <div style={{ borderTop: '1px solid #1a1a2e', margin: '8px 0' }} />;
}

// ---------------------------------------------------------------------------
// RecoveryReport — public export
// ---------------------------------------------------------------------------

export function RecoveryReport() {
  const report = usePipelineStore((s) => s.recoveryReport);

  if (!report) return null;

  const { proposed_fix: fix, validation_result: validation, counterfactual, causal_chain } = report;

  const validationColor =
    validation.status === 'PASSED' ? '#22c55e' :
    validation.status === 'PARTIAL' ? '#f59e0b' : '#ef4444';

  const recoveredCount = counterfactual?.changed_nodes?.length ?? 0;

  const rootCauseNode = causal_chain?.nodes.find(
    (n) => n.node_id === causal_chain.root_cause_node_id,
  );

  return (
    <div
      data-testid="recovery-report"
      style={{
        background: '#13131f',
        border: '1px solid #1e2030',
        borderRadius: 10,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: 12,
        color: '#c9d1d9',
        overflow: 'hidden',
        width: '100%',
      }}
    >
      {/* ── Header: RECOVERY COMPLETE + validation badge ────────── */}
      <div
        data-testid="rr-header"
        style={{
          background: 'linear-gradient(90deg, #0f2e1a 0%, #11111e 70%)',
          borderBottom: '1px solid #1e2a1e',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 14, color: '#4ade80', lineHeight: 1 }}>✓</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#4ade80', letterSpacing: '0.02em' }}>
            Recovery Complete
          </span>
        </div>
        <ValidationBadge status={validation.status} />
      </div>

      {/* ── Body ──────────────────────────────────────────────────── */}
      <div style={{ padding: '12px 14px' }}>

        {/* ── 1. What happened (plain language) ─────────────────── */}
        <div
          data-testid="rr-root-cause-summary"
          style={{
            background: 'rgba(239,68,68,0.06)',
            border: '1px solid rgba(239,68,68,0.2)',
            borderLeft: '2px solid #ef4444',
            borderRadius: 6,
            padding: '8px 10px',
            marginBottom: 10,
            fontSize: 12,
            color: '#e5e7eb',
            lineHeight: 1.5,
          }}
        >
          <div
            style={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.07em',
              textTransform: 'uppercase',
              color: '#ef4444',
              marginBottom: 3,
            }}
          >
            What Happened
          </div>
          {report.root_cause_summary}
        </div>

        {/* ── 2. Root Cause ─────────────────────────────────────── */}
        {rootCauseNode && (
          <Row label="Root Cause" testId="rr-root-cause-node" accent="#ef4444">
            <span style={{ color: '#fca5a5', fontWeight: 600 }}>{rootCauseNode.label}</span>
            {rootCauseNode.description && (
              <span style={{ color: '#8b949e', marginLeft: 5, fontSize: 11 }}>
                — {rootCauseNode.description}
              </span>
            )}
          </Row>
        )}

        <Divider />

        {/* ── 3. Proposed Fix ───────────────────────────────────── */}
        <div data-testid="rr-proposed-fix" style={{ marginBottom: 8 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 4,
            }}
          >
            <div
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: '#3b82d4',
              }}
            >
              Proposed Fix
            </div>
            <span
              data-testid="rr-fix-type-badge"
              style={{
                fontSize: 9,
                fontWeight: 600,
                color: '#3b82d4',
                background: 'rgba(59,130,212,0.1)',
                border: '1px solid rgba(59,130,212,0.2)',
                borderRadius: 6,
                padding: '1px 6px',
              }}
            >
              {FIX_TYPE_LABEL[fix.fix_type] ?? fix.fix_type}
            </span>
          </div>
          <div
            data-testid="rr-fix-description"
            style={{
              fontSize: 12,
              color: '#c9d1d9',
              lineHeight: 1.5,
              background: 'rgba(59,130,212,0.05)',
              border: '1px solid rgba(59,130,212,0.12)',
              borderRadius: 5,
              padding: '6px 8px',
              marginBottom: fix.rationale ? 4 : 0,
            }}
          >
            {fix.description}
          </div>

          {/* Fix rationale — secondary but always visible for tests */}
          {fix.rationale && (
            <div
              data-testid="rr-fix-rationale"
              style={{ fontSize: 10, color: '#57606a', lineHeight: 1.4, marginBottom: 4 }}
            >
              {fix.rationale}
            </div>
          )}

          {/* Fix confidence */}
          <div style={{ marginTop: 4 }}>
            <div style={{ fontSize: 9, color: '#3b3b5a', marginBottom: 2 }}>Fix confidence</div>
            <ConfidenceBar value={fix.confidence} color="#3b82d4" />
          </div>
        </div>

        <Divider />

        {/* ── 4. Validation ─────────────────────────────────────── */}
        <div data-testid="rr-validation-result" style={{ marginBottom: 8 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 4,
            }}
          >
            <div
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: '#57606a',
              }}
            >
              Validation
            </div>
            <ValidationBadge status={validation.status} />
          </div>
          <div
            data-testid="rr-validation-narrative"
            style={{ fontSize: 11, color: '#8b949e', lineHeight: 1.5, marginBottom: 4 }}
          >
            {validation.validation_narrative}
          </div>
          <ConfidenceBar value={validation.confidence} color={validationColor} />
        </div>

        {/* ── 5. Recovery outcome ───────────────────────────────── */}
        {counterfactual && (
          <>
            <Divider />
            <div data-testid="rr-counterfactual" style={{ marginBottom: 4 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 4,
                }}
              >
                <div
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: '#57606a',
                  }}
                >
                  Recovery Outcome
                </div>
                {recoveredCount > 0 && (
                  <span
                    data-testid="rr-recovered-count"
                    style={{
                      fontSize: 10,
                      background: '#0f2e1a',
                      color: '#4ade80',
                      border: '1px solid #22c55e',
                      borderRadius: 10,
                      padding: '1px 7px',
                      fontWeight: 700,
                    }}
                  >
                    ✓ {recoveredCount} node{recoveredCount !== 1 ? 's' : ''} recovered
                  </span>
                )}
              </div>
              <div
                data-testid="rr-counterfactual-narrative"
                style={{ fontSize: 11, color: '#8b949e', lineHeight: 1.5 }}
              >
                {counterfactual.narrative}
              </div>
            </div>
          </>
        )}

        {/* ── 6. Causal explanation — secondary, always in DOM ──── */}
        {report.causal_explanation && (
          <>
            <Divider />
            <div
              style={{
                fontSize: 9,
                fontWeight: 700,
                letterSpacing: '0.07em',
                textTransform: 'uppercase',
                color: '#3b3b5a',
                marginBottom: 3,
              }}
            >
              Causal Explanation
            </div>
            <div
              data-testid="rr-causal-explanation"
              style={{ fontSize: 10, color: '#57606a', lineHeight: 1.5 }}
            >
              {report.causal_explanation}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
