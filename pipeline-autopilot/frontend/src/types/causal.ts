/**
 * TypeScript mirrors of backend models/causal.py
 *
 * CausalNode, CausalEdge, CausalChain — the directed acyclic graph that
 * explains why a CI/CD pipeline failed.
 */

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type CausalNodeType =
  | 'CHANGE'
  | 'DEPENDENCY_BREAK'
  | 'FAILURE'
  | 'CASCADE'
  | 'ROOT_CAUSE'
  | 'FIX';

export type CausalRelation =
  | 'caused'
  | 'contributed_to'
  | 'triggered'
  | 'propagated_to';

// ---------------------------------------------------------------------------
// Graph elements
// ---------------------------------------------------------------------------

export interface CausalNode {
  node_id: string;
  node_type: CausalNodeType;
  label: string;
  description: string;
  evidence_ids: string[];
  confidence: number;   // 0.0 – 1.0
}

export interface CausalEdge {
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  relation: CausalRelation;
  explanation: string;
}

export interface CausalChain {
  chain_id: string;
  pipeline_id: string;
  nodes: CausalNode[];
  edges: CausalEdge[];
  root_cause_node_id: string;
  narrative: string;
  confidence: number;   // 0.0 – 1.0
  builder_version: string;
}
