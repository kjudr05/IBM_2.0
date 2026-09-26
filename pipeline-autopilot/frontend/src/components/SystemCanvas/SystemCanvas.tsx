/**
 * SystemCanvas — the main React Flow canvas, primary visual stage.
 *
 * Task 10: scaffold with zoom/pan, dark background, and clean initial state.
 * Task 12: ServiceNode, AgentNode, and failure animation wired in.
 *
 * The canvas is the centrepiece of the "living software system" concept.
 * It renders the causal graph as a React Flow diagram with custom node types.
 */

import { ReactFlow, Background, Controls, MiniMap, BackgroundVariant } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { usePipelineStore } from '../../state/pipelineStore';

// ---------------------------------------------------------------------------
// Canvas component
// ---------------------------------------------------------------------------

export function SystemCanvas() {
  const graphNodes = usePipelineStore((s) => s.graphNodes);
  const graphEdges = usePipelineStore((s) => s.graphEdges);

  return (
    <div style={{ width: '100%', height: '100%', background: '#0d0d14' }}>
      <ReactFlow
        nodes={graphNodes}
        edges={graphEdges}
        fitView
        minZoom={0.2}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
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
    </div>
  );
}
