/**
 * Typed fetch wrappers for all backend API endpoints.
 *
 * All requests go through the Vite dev-server proxy at /api → :8000.
 * Each function returns the typed payload or throws on HTTP error.
 *
 * Task 10: scaffold with correct types and error handling.
 * Task 11: these are called by useSSE and the App component.
 */

import type { PipelineFailureEvent } from '../types/events';
import type { RecoveryReport } from '../types/fix';

// ---------------------------------------------------------------------------
// Base helpers
// ---------------------------------------------------------------------------

const BASE = '/api';

interface ApiEnvelope<T> {
  data: T;
  error: string | null;
}

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`API ${response.status}: ${text}`);
  }

  const json = (await response.json()) as ApiEnvelope<T>;
  if (json.error) {
    throw new Error(json.error);
  }
  return json.data;
}

// ---------------------------------------------------------------------------
// /api/ingest
// ---------------------------------------------------------------------------

export interface IngestResponse {
  pipeline_id: string;
}

/**
 * POST /api/ingest — submit a raw PipelineFailureEvent.
 * Returns the pipeline_id to open the SSE stream.
 */
export async function ingestEvent(
  event: PipelineFailureEvent,
): Promise<IngestResponse> {
  return apiFetch<IngestResponse>('/ingest', {
    method: 'POST',
    body: JSON.stringify(event),
  });
}

// ---------------------------------------------------------------------------
// /api/scenarios
// ---------------------------------------------------------------------------

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  run_count: number;
}

export interface ScenariosResponse {
  scenarios: ScenarioSummary[];
}

/**
 * GET /api/scenarios — list available sample scenarios.
 */
export async function listScenarios(): Promise<ScenariosResponse> {
  return apiFetch<ScenariosResponse>('/scenarios');
}

// ---------------------------------------------------------------------------
// /api/scenarios/{id}/load
// ---------------------------------------------------------------------------

export interface LoadScenarioResponse {
  pipeline_id: string;
  scenario_id: string;
  repo: string;
  branch: string;
  commit_sha: string;
  failure_stage: string;
}

/**
 * POST /api/scenarios/{id}/load — load a sample scenario as a new pipeline run.
 * Returns the new pipeline_id.
 */
export async function loadScenario(
  scenarioId: string,
): Promise<LoadScenarioResponse> {
  return apiFetch<LoadScenarioResponse>(`/scenarios/${scenarioId}/load`, {
    method: 'POST',
  });
}

// ---------------------------------------------------------------------------
// /api/pipeline/{id}
// ---------------------------------------------------------------------------

export interface PipelineStateResponse {
  pipeline_id: string;
  repo: string;
  branch: string;
  commit_sha: string;
  pipeline_run_id: string;
  failure_stage: string;
  created_at: string;
  status: string;
  event: PipelineFailureEvent;
}

/**
 * GET /api/pipeline/{id} — full pipeline state snapshot.
 */
export async function getPipeline(
  pipelineId: string,
): Promise<PipelineStateResponse> {
  return apiFetch<PipelineStateResponse>(`/pipeline/${pipelineId}`);
}

// ---------------------------------------------------------------------------
// /api/report/{id}
// ---------------------------------------------------------------------------

/**
 * GET /api/report/{id} — final RecoveryReport JSON.
 * Throws with status 202 message if report is not yet available.
 */
export async function getReport(
  pipelineId: string,
): Promise<RecoveryReport> {
  return apiFetch<RecoveryReport>(`/report/${pipelineId}`);
}
