/**
 * CausalChainView — renders the causal chain as a vertical readable sequence.
 *
 * Task 13: full causal chain visualisation.
 *
 * Layout: each node is shown as a card. Between cards, an arrow connector
 * shows the relationship label (caused / triggered / propagated_to / contributed_to).
 * The root-cause node is highlighted prominently.
 */

import type { CausalChain, CausalNode, CausalEdge } from '../../types/causal';

// ---------------------------------------------------------------------------
// Node type → colour mapping
// ---------------------------------------------------------------------------

const NODE_TYPE_COLOUR: Record<string, string> = {
  ROOT_CAUSE:       '#ef4444',   // red — most important
  FAILURE:          '#f97316',   // orange
  CASCADE:          '#eab308',   // yellow
  DEPENDENCY_BREAK: '#a855f7',   // purple
  CHANGE:           '#3b82f6',   // blue
  FIX:              '#22c55e',   // green
};

const NODE_TYPE_LABEL: Record<string, string> = {
  ROOT_CAUSE:       'Root Cause',
  FAILURE:          'Failure',
  CASCADE:          'Cascade',
  DEPENDENCY_BREAK: 'Dependency Break',
  CHANGE:           'Change',
  FIX:              'Fix',
};

const RELATION_LABEL: Record<string, string> = {
  caused:         '→ caused',
  contributed_to: '→ contributed to',
  triggered:      '→ triggered',
  propagated_to:  '→ propagated to',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ChainNodeCardProps {
  node: CausalNode;
  isRoot: boolean;
}

function ChainNodeCard({ node, isRoot }: ChainNodeCardProps) {
  const colour = NODE_TYPE_COLOUR[node.node_type] ?? '#8b949e';
  const typeLabel = NODE_TYPE_LABEL[node.node_type] ?? node.node_type;
  const confidencePct = Math.round(node.confidence * 100);

  return (
    <div
      data-testid={`causal-node-${node.node_id}`}
      data-root={isRoot ? 'true' : 'false'}
      style={{
        background: isRoot ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.03)',
        border: `1px solid ${isRoot ? '#ef4444' : '#2a2a4a'}`,
        borderRadius: 8,
        padding: '10px 12px',
        position: 'relative',
      }}
    >
      {/* Type badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: colour,
            flexShrink: 0,
          }}
        />
        <span
          data-testid={`node-type-badge-${node.node_id}`}
          style={{ fontSize: 10, fontWeight: 600, color: colour, letterSpacing: '0.06em', textTransform: 'uppercase' }}
        >
          {typeLabel}
        </span>
        {isRoot && (
          <span
            data-testid={`root-badge-${node.node_id}`}
            style={{
              fontSize: 9,
              fontWeight: 700,
              color: '#ef4444',
              background: 'rgba(239,68,68,0.15)',
              padding: '1px 5px',
              borderRadius: 3,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
            }}
          >
            Root
          </span>
        )}
      </div>

      {/* Label */}
      <div
        data-testid={`node-label-${node.node_id}`}
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: isRoot ? '#fca5a5' : '#c9d1d9',
          marginBottom: 4,
          lineHeight: 1.4,
        }}
      >
        {node.label}
      </div>

      {/* Description */}
      {node.description && (
        <div
          data-testid={`node-description-${node.node_id}`}
          style={{ fontSize: 11, color: '#8b949e', lineHeight: 1.5 }}
        >
          {node.description}
        </div>
      )}

      {/* Confidence bar */}
      <div style={{ marginTop: 7, display: 'flex', alignItems: 'center', gap: 6 }}>
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
            data-testid={`confidence-bar-${node.node_id}`}
            style={{
              width: `${confidencePct}%`,
              height: '100%',
              background: colour,
              borderRadius: 2,
              transition: 'width 0.4s ease',
            }}
          />
        </div>
        <span style={{ fontSize: 10, color: '#57606a', flexShrink: 0 }}>
          {confidencePct}%
        </span>
      </div>
    </div>
  );
}

interface ChainConnectorProps {
  edge: CausalEdge;
}

function ChainConnector({ edge }: ChainConnectorProps) {
  const relLabel = RELATION_LABEL[edge.relation] ?? `→ ${edge.relation}`;
  return (
    <div
      data-testid={`causal-edge-${edge.edge_id}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        margin: '2px 0',
        gap: 2,
      }}
    >
      {/* Connector line */}
      <div style={{ width: 1, height: 10, background: '#2a2a4a' }} />

      {/* Relation label */}
      <span
        data-testid={`edge-relation-${edge.edge_id}`}
        style={{
          fontSize: 10,
          color: '#57606a',
          fontStyle: 'italic',
          background: '#11111e',
          padding: '1px 6px',
          borderRadius: 3,
          border: '1px solid #1e2030',
        }}
      >
        {relLabel}
      </span>

      {/* Explanation — shown if different from relation */}
      {edge.explanation && (
        <span
          data-testid={`edge-explanation-${edge.edge_id}`}
          style={{ fontSize: 10, color: '#57606a', textAlign: 'center', maxWidth: 220, lineHeight: 1.4 }}
        >
          {edge.explanation}
        </span>
      )}

      <div style={{ width: 1, height: 6, background: '#2a2a4a' }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Topological sort — produces an ordered node list for linear display
// ---------------------------------------------------------------------------

function buildOrderedNodes(chain: CausalChain): CausalNode[] {
  const nodeMap = new Map(chain.nodes.map((n) => [n.node_id, n]));
  const edgeMap = new Map<string, CausalEdge[]>();

  // Build outgoing edge map
  for (const edge of chain.edges) {
    const list = edgeMap.get(edge.source_node_id) ?? [];
    list.push(edge);
    edgeMap.set(edge.source_node_id, list);
  }

  // Find nodes with no incoming edges (sources)
  const hasIncoming = new Set(chain.edges.map((e) => e.target_node_id));
  const roots = chain.nodes.filter((n) => !hasIncoming.has(n.node_id));

  // BFS traversal
  const visited = new Set<string>();
  const ordered: CausalNode[] = [];
  const queue = [...roots];

  while (queue.length > 0) {
    const node = queue.shift()!;
    if (visited.has(node.node_id)) continue;
    visited.add(node.node_id);
    ordered.push(node);
    const outEdges = edgeMap.get(node.node_id) ?? [];
    for (const edge of outEdges) {
      const target = nodeMap.get(edge.target_node_id);
      if (target && !visited.has(target.node_id)) {
        queue.push(target);
      }
    }
  }

  // Append any unreached nodes (isolated or cycles)
  for (const node of chain.nodes) {
    if (!visited.has(node.node_id)) ordered.push(node);
  }

  return ordered;
}

// ---------------------------------------------------------------------------
// CausalChainView — public export
// ---------------------------------------------------------------------------

interface CausalChainViewProps {
  chain: CausalChain;
}

export function CausalChainView({ chain }: CausalChainViewProps) {
  const orderedNodes = buildOrderedNodes(chain);

  // Edge lookup: given (sourceId, targetId) → edge
  const edgeBetween = (a: string, b: string): CausalEdge | undefined =>
    chain.edges.find((e) => e.source_node_id === a && e.target_node_id === b);

  return (
    <div data-testid="causal-chain-view" style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {orderedNodes.map((node, idx) => {
        const isRoot = node.node_id === chain.root_cause_node_id;
        const nextNode = orderedNodes[idx + 1];
        const connector = nextNode ? edgeBetween(node.node_id, nextNode.node_id) : undefined;

        return (
          <div key={node.node_id}>
            <ChainNodeCard node={node} isRoot={isRoot} />
            {connector && <ChainConnector edge={connector} />}
            {/* If no direct edge but there is a next node, show a plain arrow */}
            {!connector && nextNode && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  margin: '4px 0',
                  color: '#2a2a4a',
                  fontSize: 14,
                }}
              >
                ↓
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
