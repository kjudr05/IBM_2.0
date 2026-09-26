/**
 * TypeScript mirrors of backend models/events.py
 *
 * PipelineFailureEvent — the ingest payload sent to POST /api/ingest.
 * Shape must match sample-data/scenario-001/failure_event.json exactly.
 */

export interface HistoricalRun {
  run_id: string;
  date: string;              // ISO-8601
  failure_stage: string | null;
  root_cause: string | null;
  fix_applied: string | null;
  resolved_in: string | null;
}

export interface PipelineFailureEvent {
  id: string;
  repo: string;
  branch: string;
  commit_sha: string;
  pipeline_run_id: string;
  timestamp: string;         // ISO-8601
  failure_stage: string;

  // Raw source data (optional — may be embedded or URL-referenced)
  raw_log_url: string | null;
  raw_log_text: string | null;
  git_diff_patch: string | null;
  test_results_xml: string | null;
  dependency_before: Record<string, unknown>;
  dependency_after: Record<string, unknown>;
  dockerfile_content: string | null;
  ci_config_content: string | null;
  history: HistoricalRun[];
}

// ---------------------------------------------------------------------------
// SSE event types emitted by GET /api/stream/{id}
// ---------------------------------------------------------------------------

export type StoryStateName =
  | 'HEALTHY'
  | 'CHANGE_DETECTED'
  | 'FAILURE_PROPAGATING'
  | 'AGENTS_ACTIVATING'
  | 'EVIDENCE_FLOWING'
  | 'EVIDENCE_CONVERGING'
  | 'ROOT_CAUSE_IDENTIFIED'
  | 'FIX_PROPOSED'
  | 'COUNTERFACTUAL_SIMULATING'
  | 'COUNTERFACTUAL_SHOWN'
  | 'SYSTEM_RECOVERING'
  | 'COMPLETE';

export interface SSEStateTransitionEvent {
  type: 'STATE_TRANSITION';
  state: StoryStateName;
  ts: string;
}

export interface SSEEvidenceArrivedEvent {
  type: 'EVIDENCE_ARRIVED';
  agent_id: string;
  evidence: Record<string, unknown>;
  ts: string;
}

export interface SSECausalChainEvent {
  type: 'CAUSAL_CHAIN';
  chain: Record<string, unknown>;
  ts: string;
}

export interface SSEFixProposedEvent {
  type: 'FIX_PROPOSED';
  fix: Record<string, unknown>;
  ts: string;
}

export interface SSEValidationResultEvent {
  type: 'VALIDATION_RESULT';
  result: Record<string, unknown>;
  ts: string;
}

export interface SSEReportReadyEvent {
  type: 'REPORT_READY';
  report_id: string;
  ts: string;
}

export interface SSEErrorEvent {
  type: 'ERROR';
  message: string;
  ts: string;
}

export type SSEEvent =
  | SSEStateTransitionEvent
  | SSEEvidenceArrivedEvent
  | SSECausalChainEvent
  | SSEFixProposedEvent
  | SSEValidationResultEvent
  | SSEReportReadyEvent
  | SSEErrorEvent;
