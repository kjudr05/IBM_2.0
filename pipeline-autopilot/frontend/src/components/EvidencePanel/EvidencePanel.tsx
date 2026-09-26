/**
 * EvidencePanel — Level 2 (causal) and Level 3 (technical) progressive disclosure.
 *
 * Task 10: minimal placeholder.
 * Task 13: full implementation.
 *
 * Structure:
 *   ┌─────────────────────────┐
 *   │  ● ROOT CAUSE FOUND     │  ← prominent non-technical headline (Level 2)
 *   │                         │
 *   │  Plain-language         │  ← narrative for non-technical judges
 *   │  narrative text         │
 *   ├─────────────────────────┤
 *   │  Causal Chain  ▾        │  ← collapsible: shows causal node sequence
 *   │  [CausalChainView]      │
 *   ├─────────────────────────┤
 *   │  Supporting Evidence  ▾ │  ← collapsible: evidence cards
 *   │  [EvidenceCard × N]     │
 *   │  [TechnicalDrill]       │  ← appears inline when a card is inspected
 *   └─────────────────────────┘
 *
 * Visibility:
 *   - Hidden (width=0, pointer-events=none) when causalChain is null.
 *   - Slides in with a CSS width transition when causalChain becomes available.
 *
 * State management:
 *   - Reads from the existing Zustand pipelineStore (causalChain, evidenceByAgent).
 *   - No second state system.
 *   - Panel-local state: which section is open, which evidence card is selected.
 */

import { useState } from 'react';
import { usePipelineStore } from '../../state/pipelineStore';
import { CausalChainView } from './CausalChain';
import { EvidenceCard } from './EvidenceCard';
import { TechnicalDrill } from './TechnicalDrill';
import type { AnyEvidence } from '../../types/evidence';

// ---------------------------------------------------------------------------
// Accordion section
// ---------------------------------------------------------------------------

interface AccordionProps {
  title: string;
  badge?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
  testId?: string;
}

function Accordion({ title, badge, defaultOpen = true, children, testId }: AccordionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      data-testid={testId}
      style={{ borderTop: '1px solid #1e2030' }}
    >
      <button
        data-testid={testId ? `${testId}-toggle` : undefined}
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 0',
          color: '#8b949e',
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {title}
          {badge !== undefined && badge > 0 && (
            <span
              style={{
                fontSize: 9,
                background: '#1e2030',
                color: '#57606a',
                borderRadius: 10,
                padding: '1px 5px',
                fontWeight: 600,
              }}
            >
              {badge}
            </span>
          )}
        </span>
        <span style={{ color: '#57606a', fontSize: 10, marginLeft: 8 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div data-testid={testId ? `${testId}-content` : undefined} style={{ paddingBottom: 12 }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root-cause headline
// ---------------------------------------------------------------------------

interface RootCauseHeadlineProps {
  label: string;
  description: string;
  narrative: string;
  confidence: number;
}

function RootCauseHeadline({ label, description, narrative, confidence }: RootCauseHeadlineProps) {
  const confidencePct = Math.round(confidence * 100);
  return (
    <div
      data-testid="root-cause-headline"
      style={{
        background: 'rgba(239,68,68,0.07)',
        border: '1px solid rgba(239,68,68,0.3)',
        borderRadius: 10,
        padding: '12px 14px',
        marginBottom: 14,
      }}
    >
      {/* Status pill */}
      <div
        data-testid="root-cause-status-pill"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          fontSize: 10,
          fontWeight: 700,
          color: '#ef4444',
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          marginBottom: 6,
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#ef4444',
            display: 'inline-block',
          }}
        />
        Root Cause Identified
      </div>

      {/* Root-cause node label — bold, large */}
      <div
        data-testid="root-cause-label"
        style={{
          fontSize: 15,
          fontWeight: 700,
          color: '#fca5a5',
          lineHeight: 1.3,
          marginBottom: 5,
        }}
      >
        {label}
      </div>

      {/* Short description */}
      {description && (
        <div
          data-testid="root-cause-description"
          style={{ fontSize: 12, color: '#c9d1d9', lineHeight: 1.5, marginBottom: 8 }}
        >
          {description}
        </div>
      )}

      {/* Plain-language narrative — most prominent for non-technical readers */}
      <div
        data-testid="root-cause-narrative"
        style={{
          fontSize: 12,
          color: '#c9d1d9',
          lineHeight: 1.6,
          background: 'rgba(0,0,0,0.2)',
          borderRadius: 6,
          padding: '8px 10px',
          marginBottom: 8,
          borderLeft: '2px solid rgba(239,68,68,0.4)',
        }}
      >
        {narrative}
      </div>

      {/* Confidence */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div
          style={{
            flex: 1,
            height: 4,
            background: '#1e2030',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            data-testid="root-cause-confidence-bar"
            style={{
              width: `${confidencePct}%`,
              height: '100%',
              background: confidencePct >= 80 ? '#ef4444' : confidencePct >= 50 ? '#f97316' : '#eab308',
              borderRadius: 2,
              transition: 'width 0.5s ease',
            }}
          />
        </div>
        <span
          data-testid="root-cause-confidence-pct"
          style={{ fontSize: 10, color: '#57606a', flexShrink: 0 }}
        >
          {confidencePct}% confidence
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// EvidencePanel — public export
// ---------------------------------------------------------------------------

export function EvidencePanel() {
  const causalChain    = usePipelineStore((s) => s.causalChain);
  const evidenceByAgent = usePipelineStore((s) => s.evidenceByAgent);

  // Which evidence card is currently being inspected (TechnicalDrill shown)
  const [inspectedEvId, setInspectedEvId] = useState<string | null>(null);

  // Convert evidence map to array, sorted for stable display
  const evidenceList: AnyEvidence[] = Object.values(evidenceByAgent).sort((a, b) =>
    a.evidence_type.localeCompare(b.evidence_type),
  );

  // Panel visibility: visible when causal chain has arrived
  const visible = causalChain !== null;

  // Find the root-cause node
  const rootNode = causalChain?.nodes.find(
    (n) => n.node_id === causalChain.root_cause_node_id,
  );

  function handleInspect(ev: AnyEvidence) {
    setInspectedEvId((prev) => (prev === ev.evidence_id ? null : ev.evidence_id));
  }

  return (
    <aside
      data-testid="evidence-panel"
      data-visible={visible ? 'true' : 'false'}
      style={{
        width: visible ? 340 : 0,
        minWidth: visible ? 340 : 0,
        maxWidth: 340,
        height: '100%',
        overflow: 'hidden',
        background: '#11111e',
        borderLeft: '1px solid #1e2030',
        transition: 'width 0.3s ease, min-width 0.3s ease',
        pointerEvents: visible ? 'auto' : 'none',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}
    >
      {visible && causalChain && (
        <div
          style={{
            padding: '16px 14px',
            display: 'flex',
            flexDirection: 'column',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: 13,
            color: '#c9d1d9',
            overflowY: 'auto',
            overflowX: 'hidden',
            height: '100%',
            /* Custom scrollbar to match dark theme */
            scrollbarWidth: 'thin' as 'thin',
            scrollbarColor: '#2a2a4a #11111e',
          }}
        >
          {/* Panel header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 14,
            }}
          >
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: '#57606a',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              Analysis
            </span>
            <span
              data-testid="pipeline-id-label"
              style={{ fontSize: 10, color: '#3b3b5a' }}
            >
              {causalChain.pipeline_id.slice(-8)}
            </span>
          </div>

          {/* ── Level 2: Plain-language root cause headline ─────────── */}
          {rootNode && (
            <RootCauseHeadline
              label={rootNode.label}
              description={rootNode.description}
              narrative={causalChain.narrative}
              confidence={causalChain.confidence}
            />
          )}

          {/* ── Level 2: Causal chain sequence ──────────────────────── */}
          <Accordion
            title="Causal Chain"
            badge={causalChain.nodes.length}
            testId="accordion-causal-chain"
          >
            <CausalChainView chain={causalChain} />
          </Accordion>

          {/* ── Level 3: Supporting evidence ────────────────────────── */}
          {evidenceList.length > 0 && (
            <Accordion
              title="Supporting Evidence"
              badge={evidenceList.length}
              defaultOpen={false}
              testId="accordion-evidence"
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {evidenceList.map((ev) => {
                  const isActive = inspectedEvId === ev.evidence_id;
                  return (
                    <div key={ev.evidence_id}>
                      <EvidenceCard
                        evidence={ev}
                        onInspect={handleInspect}
                        active={isActive}
                      />
                      {isActive && (
                        <TechnicalDrill evidence={ev} />
                      )}
                    </div>
                  );
                })}
              </div>
            </Accordion>
          )}
        </div>
      )}
    </aside>
  );
}
