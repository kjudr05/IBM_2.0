/**
 * SystemCanvas — the main React Flow canvas, primary visual stage.
 *
 * Task 10: scaffold with zoom/pan, dark background, and clean initial state.
 * Task 12: ServiceNode, AgentNode, and failure animation wired in.
 * Runtime fix: fitView with padding, controlled via useEffect when nodes arrive.
 *
 * The canvas is the centrepiece of the "living software system" concept.
 * It renders the causal graph as a React Flow diagram with custom node types.
 *
 * Custom node types registered here (Task 12):
 *   serviceNode  → ServiceNode   (health ring + status colours)
 *   agentNode    → AgentNode     (hexagon, active/idle)
 *   evidenceNode → EvidenceNode  (placeholder, Task 13+)
 *
 * Custom edge types registered here (Task 12):
 *   animatedEdge  → AnimatedEdge  (grey dash, default)
 *   failureEdge   → FailureEdge   (red particle stream)
 *   evidenceEdge  → EvidenceEdge  (blue dot stream)
 *   healthyEdge   → HealthyEdge   (grey dash alias)
 */

import { useEffect, useCallback } from 'react';
import { ReactFlow, Background, Controls, MiniMap, BackgroundVariant, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { usePipelineStore } from '../../state/pipelineStore';
import { ServiceNode } from './nodes/ServiceNode';
import { AgentNode }   from './nodes/AgentNode';
import { EvidenceNode } from './nodes/EvidenceNode';
import {
  AnimatedEdge,
  FailureEdge,
  EvidenceEdge,
  HealthyEdge,
} from './edges/AnimatedEdge';

// ---------------------------------------------------------------------------
// Custom type maps — defined outside the component so React Flow doesn't
// recreate them on every render (which would cause node remounts).
// ---------------------------------------------------------------------------

const NODE_TYPES = {
  serviceNode:  ServiceNode,
  agentNode:    AgentNode,
  evidenceNode: EvidenceNode,
} as const;

const EDGE_TYPES = {
  animatedEdge: AnimatedEdge,
  failureEdge:  FailureEdge,
  evidenceEdge: EvidenceEdge,
  healthyEdge:  HealthyEdge,
} as const;

// ---------------------------------------------------------------------------
// Inner canvas — must be rendered inside ReactFlowProvider to use useReactFlow
// ---------------------------------------------------------------------------

function CanvasInner() {
  const graphNodes = usePipelineStore((s) => s.graphNodes);
  const graphEdges = usePipelineStore((s) => s.graphEdges);
  const { fitView } = useReactFlow();

  // Re-fit whenever nodes change (initial load + dynamic additions).
  // Use generous padding (0.18) so the full graph — services + agents —
  // is comfortably visible with room left for the CounterfactualSplit overlay.
  const handleFit = useCallback(() => {
    setTimeout(() => {
      fitView({ padding: 0.18, maxZoom: 0.9, duration: 400 });
    }, 60);
  }, [fitView]);

  useEffect(() => {
    if (graphNodes.length > 0) {
      handleFit();
    }
  }, [graphNodes.length, handleFit]);

  return (
    <ReactFlow
      nodes={graphNodes}
      edges={graphEdges}
      nodeTypes={NODE_TYPES}
      edgeTypes={EDGE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.18, maxZoom: 0.9 }}
      minZoom={0.12}
      maxZoom={2}
      defaultViewport={{ x: 0, y: 0, zoom: 0.75 }}
      proOptions={{ hideAttribution: true }}
    >
      {/* Subtle dot grid background */}
      <Background
        variant={BackgroundVariant.Dots}
        gap={28}
        size={1}
        color="#1e2030"
      />

      {/* Zoom / fit controls */}
      <Controls
        style={{
          background: '#1a1a2e',
          border: '1px solid #2a2a4a',
          borderRadius: 8,
        }}
      />

      {/* Mini-map for large graphs */}
      <MiniMap
        style={{
          background: '#1a1a2e',
          border: '1px solid #2a2a4a',
        }}
        nodeColor="#3b82d4"
        maskColor="rgba(13,13,20,0.7)"
      />
    </ReactFlow>
  );
}

// ---------------------------------------------------------------------------
// Canvas component — wraps inner canvas, provides its own size container
// ---------------------------------------------------------------------------

export function SystemCanvas() {
  return (
    <div style={{ width: '100%', height: '100%', background: '#0d0d14' }}>
      <CanvasInner />
    </div>
  );
}
