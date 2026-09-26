/**
 * App — root application component.
 *
 * Task 10: establishes the full-screen dark layout with:
 *   - StoryBar at the top (12-step progress strip)
 *   - SystemCanvas in the centre (React Flow canvas, primary visual stage)
 *   - EvidencePanel as a right sidebar (appears when causal chain is available)
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────┐
 *   │  StoryBar (top strip, 48px)                      │
 *   ├─────────────────────────────────────┬────────────┤
 *   │                                     │            │
 *   │  SystemCanvas (React Flow, flex-1)  │  Evidence  │
 *   │                                     │   Panel    │
 *   │                                     │  (320px,   │
 *   │                                     │  optional) │
 *   └─────────────────────────────────────┴────────────┘
 *
 * Later tasks add the LoadScenario button, ReplayControls, and
 * CounterfactualSplit overlay without changing this outer shell.
 */

import { ReactFlowProvider } from '@xyflow/react';
import { SystemCanvas } from './components/SystemCanvas/SystemCanvas';
import { StoryBar } from './components/StoryBar/StoryBar';
import { EvidencePanel } from './components/EvidencePanel/EvidencePanel';
import { RecoveryReport } from './components/RecoveryReport/RecoveryReport';
import { usePipelineStore } from './state/pipelineStore';
import { useSSE } from './hooks/useSSE';
import { loadScenario } from './api/client';

// ---------------------------------------------------------------------------
// Inline global reset — keeps bundle self-contained, no external CSS needed
// ---------------------------------------------------------------------------

const globalStyle = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body, #root { width: 100%; height: 100%; overflow: hidden; }
  body { background: #0d0d14; color: #c9d1d9; font-family: system-ui, -apple-system, sans-serif; }
`;

export function App() {
  const pipelineId = usePipelineStore((s) => s.pipelineId);
  const storyState = usePipelineStore((s) => s.storyState);
  const error = usePipelineStore((s) => s.error);
  const isStreaming = usePipelineStore((s) => s.isStreaming);
  const setPipelineId = usePipelineStore((s) => s.setPipelineId);
  const setError = usePipelineStore((s) => s.setError);

  // Wire SSE stream: opens when pipelineId is set, closes on unmount/change.
  useSSE(pipelineId);

  async function handleLoadDemo() {
    try {
      setError(null);
      const result = await loadScenario('001');
      setPipelineId(result.pipeline_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <>
      {/* Inline global CSS reset */}
      <style>{globalStyle}</style>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
          height: '100%',
          background: '#0d0d14',
        }}
      >
        {/* ── Story Bar ──────────────────────────────────────────── */}
        <div
          style={{
            height: 48,
            flexShrink: 0,
            background: '#11111e',
            borderBottom: '1px solid #1e2030',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {/* Brand */}
          <span
            style={{
              padding: '0 16px',
              fontWeight: 600,
              fontSize: 13,
              color: '#3b82d4',
              letterSpacing: '0.05em',
              whiteSpace: 'nowrap',
            }}
          >
            Pipeline Autopilot
          </span>

          {/* 12-step progress strip */}
          <div style={{ flex: 1, height: '100%' }}>
            <StoryBar />
          </div>

          {/* Load demo button */}
          {!pipelineId && (
            <button
              onClick={() => void handleLoadDemo()}
              style={{
                margin: '0 16px',
                padding: '6px 14px',
                borderRadius: 6,
                border: '1px solid #3b82d4',
                background: 'transparent',
                color: '#3b82d4',
                fontSize: 12,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Load Demo
            </button>
          )}

          {/* Pipeline id indicator + streaming dot */}
          {pipelineId && (
            <span
              style={{
                margin: '0 16px',
                fontSize: 11,
                color: '#57606a',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              {isStreaming && (
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: '#3b82d4',
                    display: 'inline-block',
                  }}
                />
              )}
              {storyState}
            </span>
          )}
        </div>

        {/* ── Main area ──────────────────────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* React Flow canvas */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <ReactFlowProvider>
              <SystemCanvas />
            </ReactFlowProvider>
          </div>

          {/* Evidence panel (shown after causal chain arrives) */}
          <EvidencePanel />
        </div>

        {/* ── Error toast ────────────────────────────────────────── */}
        {error && (
          <div
            style={{
              position: 'fixed',
              bottom: 24,
              left: '50%',
              transform: 'translateX(-50%)',
              padding: '10px 20px',
              background: '#2d1b1b',
              border: '1px solid #6b2020',
              borderRadius: 8,
              color: '#f87171',
              fontSize: 13,
              zIndex: 1000,
            }}
          >
            {error}
          </div>
        )}

        {/* ── Recovery report overlay ─────────────────────────────── */}
        {storyState === 'COMPLETE' && (
          <div
            style={{
              position: 'fixed',
              bottom: 24,
              right: 24,
              zIndex: 100,
              maxWidth: 400,
            }}
          >
            <RecoveryReport />
          </div>
        )}
      </div>
    </>
  );
}
