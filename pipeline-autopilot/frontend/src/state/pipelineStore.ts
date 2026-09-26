/**
 * Zustand pipeline store — holds all live state for the visual story.
 *
 * Task 10: establishes the store shape, initial state, and action types.
 * Task 11: wires SSE events into the store actions.
 *
 * Store fields (plan §5)
 * ----------------------
 * storyState       — current position in the 12-step visual story
 * pipelineId       — active pipeline being investigated (null = idle)
 * graphNodes       — React Flow nodes rendered on the canvas
 * graphEdges       — React Flow edges rendered on the canvas
 * evidenceByAgent  — map of agent_id → evidence artifact
 * causalChain      — the assembled causal DAG
 * proposedFix      — the generated fix proposal
 * validationResult — outcome of the deterministic validation
 * counterfactual   — before/after system snapshots
 * recoveryReport   — final report (available after COMPLETE)
 * error            — last error message (or null)
 */

import { create } from 'zustand';
import type { Node, Edge } from '@xyflow/react';
import type { StoryState } from './storyMachine';
import type { AnyEvidence } from '../types/evidence';
import type { CausalChain } from '../types/causal';
import type { FixProposal, ValidationResult, CounterfactualResult, RecoveryReport } from '../types/fix';
import { INITIAL_GRAPH_NODES, INITIAL_GRAPH_EDGES } from './initialGraph';

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

export interface PipelineState {
  // Story progression
  storyState: StoryState;

  // Active pipeline
  pipelineId: string | null;

  // React Flow canvas data
  graphNodes: Node[];
  graphEdges: Edge[];

  // Investigation outputs
  evidenceByAgent: Record<string, AnyEvidence>;
  causalChain: CausalChain | null;
  proposedFix: FixProposal | null;
  validationResult: ValidationResult | null;
  counterfactual: CounterfactualResult | null;
  recoveryReport: RecoveryReport | null;

  // UI state
  error: string | null;
  isStreaming: boolean;
}

// ---------------------------------------------------------------------------
// Store actions
// ---------------------------------------------------------------------------

export interface PipelineActions {
  // Lifecycle
  setPipelineId: (id: string) => void;
  reset: () => void;

  // Story machine
  setStoryState: (state: StoryState) => void;

  // Graph
  setGraphNodes: (nodes: Node[]) => void;
  setGraphEdges: (edges: Edge[]) => void;

  // Investigation data (set by SSE handler in Task 11)
  setEvidenceForAgent: (agentId: string, evidence: AnyEvidence) => void;
  setCausalChain: (chain: CausalChain) => void;
  setProposedFix: (fix: FixProposal) => void;
  setValidationResult: (result: ValidationResult) => void;
  setCounterfactual: (cf: CounterfactualResult) => void;
  setRecoveryReport: (report: RecoveryReport) => void;

  // Status
  setError: (message: string | null) => void;
  setIsStreaming: (streaming: boolean) => void;
}

export type PipelineStore = PipelineState & PipelineActions;

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

const INITIAL_STATE: PipelineState = {
  storyState: 'HEALTHY',
  pipelineId: null,
  graphNodes: INITIAL_GRAPH_NODES,
  graphEdges: INITIAL_GRAPH_EDGES,
  evidenceByAgent: {},
  causalChain: null,
  proposedFix: null,
  validationResult: null,
  counterfactual: null,
  recoveryReport: null,
  error: null,
  isStreaming: false,
};

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const usePipelineStore = create<PipelineStore>((set) => ({
  ...INITIAL_STATE,

  // Lifecycle
  setPipelineId: (id) => set({ pipelineId: id }),
  reset: () => set(INITIAL_STATE),

  // Story machine
  setStoryState: (storyState) => set({ storyState }),

  // Graph
  setGraphNodes: (graphNodes) => set({ graphNodes }),
  setGraphEdges: (graphEdges) => set({ graphEdges }),

  // Investigation data
  setEvidenceForAgent: (agentId, evidence) =>
    set((s) => ({
      evidenceByAgent: { ...s.evidenceByAgent, [agentId]: evidence },
    })),
  setCausalChain: (causalChain) => set({ causalChain }),
  setProposedFix: (proposedFix) => set({ proposedFix }),
  setValidationResult: (validationResult) => set({ validationResult }),
  setCounterfactual: (counterfactual) => set({ counterfactual }),
  setRecoveryReport: (recoveryReport) => set({ recoveryReport }),

  // Status
  setError: (error) => set({ error }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
}));
