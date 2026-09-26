/**
 * TypeScript mirrors of backend models/evidence.py
 *
 * All evidence artifact types that investigators produce.
 * Each extends BaseEvidence with a discriminated evidence_type field.
 */

// ---------------------------------------------------------------------------
// Shared sub-types
// ---------------------------------------------------------------------------

export interface EvidenceSource {
  agent_id: string;
  input_file: string | null;
  provider: string | null;
}

export interface ChangedFile {
  path: string;
  additions: number;
  deletions: number;
  diff_hunk: string | null;
}

export interface DepChange {
  name: string;
  old_version: string | null;
  new_version: string | null;
  affected_component: string | null;
}

export interface FailedTest {
  name: string;
  class_name: string | null;
  failure_message: string;
  duration_ms: number | null;
}

export interface SimilarFailure {
  run_id: string;
  date: string;
  root_cause: string | null;
  fix_applied: string | null;
  similarity_score: number;
}

// ---------------------------------------------------------------------------
// Base evidence fields (shared across all types)
// ---------------------------------------------------------------------------

export interface BaseEvidence {
  evidence_id: string;
  pipeline_id: string;
  evidence_type: EvidenceType;
  source: EvidenceSource;
  created_at: string;    // ISO-8601
  confidence: number;    // 0.0 – 1.0
  summary: string;
}

export type EvidenceType =
  | 'failure'
  | 'change'
  | 'dependency'
  | 'test'
  | 'infra'
  | 'historical';

// ---------------------------------------------------------------------------
// Concrete evidence artifact types
// ---------------------------------------------------------------------------

export interface FailureEvidence extends BaseEvidence {
  evidence_type: 'failure';
  error_class: string;
  error_message: string;
  stack_trace: string[];
  affected_stage: string;
  failure_timestamp: string;
  severity: string | null;
  log_excerpt: string | null;
  file_path: string | null;
  line_number: number | null;
}

export interface ChangeEvidence extends BaseEvidence {
  evidence_type: 'change';
  commit_sha: string;
  author: string | null;
  commit_message: string | null;
  commit_timestamp: string | null;
  changed_files: ChangedFile[];
  changed_functions: string[];
  total_additions: number;
  total_deletions: number;
}

export interface DependencyEvidence extends BaseEvidence {
  evidence_type: 'dependency';
  added: DepChange[];
  removed: DepChange[];
  changed: DepChange[];
  breaking_changes: string[];
}

export interface TestRunEvidence extends BaseEvidence {
  evidence_type: 'test';
  failed_tests: FailedTest[];
  flaky_tests: string[];
  regression_tests: string[];
  total_run: number;
  total_failed: number;
  total_passed: number;
  total_skipped: number;
}

export interface InfraEvidence extends BaseEvidence {
  evidence_type: 'infra';
  dockerfile_issues: string[];
  ci_config_issues: string[];
  env_var_issues: string[];
  image_changes: string[];
  config_source: string | null;
}

export interface HistoricalEvidence extends BaseEvidence {
  evidence_type: 'historical';
  similar_failures: SimilarFailure[];
  recurrence_count: number;
  last_seen: string | null;
  known_fix: string | null;
}

// Discriminated union for all evidence artifacts
export type AnyEvidence =
  | FailureEvidence
  | ChangeEvidence
  | DependencyEvidence
  | TestRunEvidence
  | InfraEvidence
  | HistoricalEvidence;
