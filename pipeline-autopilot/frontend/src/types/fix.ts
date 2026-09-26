/**
 * TypeScript mirrors of backend models/fix.py and models/report.py
 *
 * FixProposal, ValidationResult, RecoveryReport
 */

import type { CausalChain } from './causal';
import type { DepChange } from './evidence';

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type FixType =
  | 'DEPENDENCY_CHANGE'
  | 'CODE_PATCH'
  | 'CONFIG_CHANGE'
  | 'ENV_FIX';

export type ValidationStatus = 'PASSED' | 'FAILED' | 'PARTIAL';

// ---------------------------------------------------------------------------
// FixProposal
// ---------------------------------------------------------------------------

export interface FixProposal {
  fix_id: string;
  pipeline_id: string;
  root_cause_node_id: string;
  fix_type: FixType;
  description: string;
  rationale: string;
  affected_file: string | null;
  dependency_changes: DepChange[];
  patch: string | null;
  config_changes: Record<string, string> | null;
  evidence_ids: string[];
  confidence: number;   // 0.0 – 1.0
  generator_version: string;
}

// ---------------------------------------------------------------------------
// ValidationResult
// ---------------------------------------------------------------------------

export interface ValidationResult {
  validation_id: string;
  fix_id: string;
  status: ValidationStatus;
  confidence: number;
  validation_narrative: string;
}

// ---------------------------------------------------------------------------
// Counterfactual (from simulation/counterfactual.py)
// ---------------------------------------------------------------------------

export type NodeHealth = 'HEALTHY' | 'DEGRADED' | 'FAILED';

export interface SystemSnapshot {
  nodes: Record<string, NodeHealth>;
}

export interface CounterfactualResult {
  pipeline_id: string;
  fix_id: string;
  before_state: SystemSnapshot;
  after_state: SystemSnapshot;
  changed_nodes: string[];
  narrative: string;
}

// ---------------------------------------------------------------------------
// RecoveryReport
// ---------------------------------------------------------------------------

export interface RecoveryReport {
  report_id: string;
  pipeline_id: string;
  created_at: string;
  root_cause_summary: string;
  causal_explanation: string;
  evidence_summary: Record<string, { evidence_type: string; summary: string; confidence: number }>;
  proposed_fix: FixProposal;
  validation_result: ValidationResult;
  causal_chain: CausalChain;
  counterfactual: CounterfactualResult;
}
