/**
 * CounterfactualSplit — side-by-side BEFORE / AFTER view of system node states.
 *
 * Task 10: minimal placeholder that TypeScript-compiles cleanly.
 * Task 14: full split view with before/after node health colours and animated
 *          FAILED → HEALTHY transition using Framer Motion.
 *
 * Visibility:
 *   - Hidden when counterfactual is null.
 *   - Slides in from below when counterfactual arrives
 *     (story states: COUNTERFACTUAL_SIMULATING, COUNTERFACTUAL_SHOWN, SYSTEM_RECOVERING, COMPLETE).
 *
 * Architecture:
 *   - Reads CounterfactualResult from usePipelineStore (Zustand).
 *   - Re-uses the health colour palette from ServiceNode (defined locally here
 *     to avoid importing a React Flow component outside its canvas context).
 *   - Framer Motion AnimatePresence + motion.div for the slide-in and node transition.
 *   - No second state-management system.
 *   - Does not touch SystemCanvas or EvidencePanel.
 */

import { AnimatePresence, motion } from 'framer-motion';
import { usePipelineStore } from '../../state/pipelineStore';
import type { NodeHealth } from '../../types/fix';

// ---------------------------------------------------------------------------
// Health palette — mirrors ServiceNode.tsx (no import to avoid RF context issues)
// ---------------------------------------------------------------------------

const HEALTH_PALETTE: Record<NodeHealth, { ring: string; bg: string; text: string; label: string }> = {
  HEALTHY:  { ring: '#22c55e', bg: '#0f2e1a', text: '#4ade80', label: 'HEALTHY'  },
  DEGRADED: { ring: '#f59e0b', bg: '#2e1e00', text: '#fbbf24', label: 'DEGRADED' },
  FAILED:   { ring: '#ef4444', bg: '#2e0f0f', text: '#f87171', label: 'FAILED'   },
};

// ---------------------------------------------------------------------------
// NodeHealthCard — a single service node rendered as a status card
// ---------------------------------------------------------------------------

interface NodeHealthCardProps {
  nodeId: string;
  health: NodeHealth;
  /** When true the card animates in with a green glow to signal recovery */
  recovering?: boolean;
}

function NodeHealthCard({ nodeId, health, recovering = false }: NodeHealthCardProps) {
  const palette = HEALTH_PALETTE[health];

  // Prettier display name: replace underscores with spaces, capitalise words
  const displayName = nodeId
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <motion.div
      data-testid="cf-node-card"
      data-node-id={nodeId}
      data-health={health}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{
        opacity: 1,
        scale: 1,
        boxShadow: recovering
          ? [`0 0 0 0 rgba(34,197,94,0)`, `0 0 10px 3px rgba(34,197,94,0.5)`, `0 0 0 0 rgba(34,197,94,0)`]
          : 'none',
      }}
      transition={{
        duration: recovering ? 1.2 : 0.35,
        ease: 'easeOut',
        boxShadow: recovering ? { repeat: 1, duration: 1.2 } : undefined,
      }}
      style={{
        padding: '5px 10px',
        borderRadius: 6,
        background: palette.bg,
        border: `1.5px solid ${palette.ring}`,
        minWidth: 100,
        maxWidth: 140,
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        userSelect: 'none',
      }}
    >
      {/* Service name */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#c9d1d9',
          marginBottom: 3,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {displayName}
      </div>

      {/* Status pill */}
      <div
        data-testid="cf-health-pill"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          fontSize: 9,
          fontWeight: 700,
          color: palette.text,
          background: 'rgba(0,0,0,0.25)',
          borderRadius: 10,
          padding: '1px 6px',
          border: `1px solid ${palette.ring}`,
        }}
      >
        <span
          data-testid="cf-health-dot"
          style={{
            width: 5,
            height: 5,
            borderRadius: '50%',
            background: palette.ring,
            display: 'inline-block',
            flexShrink: 0,
          }}
        />
        {palette.label}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// NodeGrid — renders a set of node health cards
// ---------------------------------------------------------------------------

interface NodeGridProps {
  nodes: Record<string, NodeHealth>;
  changedNodes?: string[];
  side: 'before' | 'after';
}

function NodeGrid({ nodes, changedNodes = [], side }: NodeGridProps) {
  const entries = Object.entries(nodes);
  if (entries.length === 0) {
    return (
      <div
        style={{ color: '#57606a', fontSize: 12, padding: '12px 0', textAlign: 'center' }}
      >
        No nodes
      </div>
    );
  }

  return (
    <div
      data-testid={`cf-node-grid-${side}`}
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        justifyContent: 'center',
      }}
    >
      {entries.map(([nodeId, health]) => (
        <NodeHealthCard
          key={nodeId}
          nodeId={nodeId}
          health={health}
          recovering={side === 'after' && changedNodes.includes(nodeId)}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PanelColumn — one side of the split (BEFORE or AFTER)
// ---------------------------------------------------------------------------

interface PanelColumnProps {
  label: string;
  sublabel: string;
  accentColor: string;
  nodes: Record<string, NodeHealth>;
  changedNodes?: string[];
  side: 'before' | 'after';
  testId: string;
}

function PanelColumn({
  label,
  sublabel,
  accentColor,
  nodes,
  changedNodes,
  side,
  testId,
}: PanelColumnProps) {
  return (
    <div
      data-testid={testId}
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        padding: '0 10px',
        minWidth: 0,
      }}
    >
      {/* Column header */}
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            display: 'inline-block',
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase' as const,
            color: accentColor,
            borderBottom: `2px solid ${accentColor}`,
            paddingBottom: 2,
            marginBottom: 2,
          }}
        >
          {label}
        </div>
        <div style={{ fontSize: 10, color: '#57606a' }}>{sublabel}</div>
      </div>

      {/* Node grid */}
      <NodeGrid nodes={nodes} changedNodes={changedNodes} side={side} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// CounterfactualSplit — public export
// ---------------------------------------------------------------------------

export function CounterfactualSplit() {
  const counterfactual = usePipelineStore((s) => s.counterfactual);
  const storyState     = usePipelineStore((s) => s.storyState);

  // Visible in the three states where counterfactual is relevant
  const VISIBLE_STATES = new Set([
    'COUNTERFACTUAL_SIMULATING',
    'COUNTERFACTUAL_SHOWN',
    'SYSTEM_RECOVERING',
    'COMPLETE',
  ]);
  const visible = counterfactual !== null && VISIBLE_STATES.has(storyState);

  return (
    <AnimatePresence>
      {visible && counterfactual && (
        <motion.div
          data-testid="counterfactual-split"
          key="cf-split"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 30 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            maxHeight: '26%',
            background: 'rgba(11,11,18,0.98)',
            borderTop: '1px solid #252540',
            zIndex: 50,
            fontFamily: 'system-ui, -apple-system, sans-serif',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* ── Compact header row ──────────────────────────────────── */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 16px',
              borderBottom: '1px solid #1e2030',
              flexShrink: 0,
            }}
          >
            <span
              data-testid="cf-title"
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: '#57606a',
                letterSpacing: '0.07em',
                textTransform: 'uppercase',
              }}
            >
              Counterfactual Analysis
            </span>
            {counterfactual.changed_nodes.length > 0 && (
              <span
                data-testid="cf-changed-count"
                style={{
                  fontSize: 9,
                  background: '#0f2e1a',
                  color: '#4ade80',
                  border: '1px solid #22c55e',
                  borderRadius: 10,
                  padding: '1px 7px',
                }}
              >
                {counterfactual.changed_nodes.length} node
                {counterfactual.changed_nodes.length !== 1 ? 's' : ''} recovered
              </span>
            )}
            {/* Narrative inline to save vertical space */}
            <span
              data-testid="cf-narrative"
              style={{
                fontSize: 11,
                color: '#8b949e',
                marginLeft: 4,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                flex: 1,
              }}
            >
              {counterfactual.narrative}
            </span>
          </div>

          {/* ── Before / After columns ─────────────────────────────── */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              padding: '8px 16px 10px',
              gap: 0,
              overflowY: 'auto',
              overflowX: 'hidden',
              flex: 1,
              minHeight: 0,
            }}
          >
            {/* BEFORE column */}
            <PanelColumn
              testId="cf-before-panel"
              label="Before Fix"
              sublabel="Broken state"
              accentColor="#ef4444"
              nodes={counterfactual.before_state.nodes}
              side="before"
            />

            {/* Divider arrow */}
            <div
              data-testid="cf-arrow"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                padding: '0 8px',
                color: '#3b82d4',
                fontSize: 18,
                alignSelf: 'center',
              }}
            >
              →
            </div>

            {/* AFTER column */}
            <PanelColumn
              testId="cf-after-panel"
              label="After Fix"
              sublabel="Recovered state"
              accentColor="#22c55e"
              nodes={counterfactual.after_state.nodes}
              changedNodes={counterfactual.changed_nodes}
              side="after"
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
