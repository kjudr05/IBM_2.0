/**
 * App — root application component.
 *
 * Layout:
 *   ┌──────────────────────────────────────────────────┐
 *   │  Header: Brand | StoryBar | Button/Status (48px) │
 *   ├──────────────────────────────────────────────────┤
 *   │  Caption bar (24px, current story phase)         │
 *   ├─────────────────────────────────────┬────────────┤
 *   │                                     │            │
 *   │  SystemCanvas (React Flow, flex-1)  │  Evidence  │
 *   │  + CounterfactualSplit overlay      │   Panel    │
 *   │                                     │  (340px)   │
 *   │                                     │            │
 *   └─────────────────────────────────────┴────────────┘
 *   │  RecoveryReport (bottom strip, COMPLETE only)    │
 *   └──────────────────────────────────────────────────┘
 */

import { ReactFlowProvider } from '@xyflow/react';
import { SystemCanvas } from './components/SystemCanvas/SystemCanvas';
import { StoryBar } from './components/StoryBar/StoryBar';
import { EvidencePanel } from './components/EvidencePanel/EvidencePanel';
import { RecoveryReport } from './components/RecoveryReport/RecoveryReport';
import { CounterfactualSplit } from './components/CounterfactualSplit/CounterfactualSplit';
import { usePipelineStore } from './state/pipelineStore';
import { useSSE } from './hooks/useSSE';
import { loadScenario } from './api/client';
import { getStoryStep } from './state/storyMachine';

// ---------------------------------------------------------------------------
// Inline global reset — keeps bundle self-contained, no external CSS needed
// ---------------------------------------------------------------------------

const globalStyle = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body, #root { width: 100%; height: 100%; overflow: hidden; }
  body { background: #0d0d14; color: #c9d1d9; font-family: system-ui, -apple-system, sans-serif; }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0d0d14; }
  ::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #3b82d4; }
`;

export function App() {
  const pipelineId   = usePipelineStore((s) => s.pipelineId);
  const storyState   = usePipelineStore((s) => s.storyState);
  const recoveryReport = usePipelineStore((s) => s.recoveryReport);
  const error        = usePipelineStore((s) => s.error);
  const isStreaming  = usePipelineStore((s) => s.isStreaming);
  const setPipelineId = usePipelineStore((s) => s.setPipelineId);
  const setError     = usePipelineStore((s) => s.setError);

  // Wire SSE stream: opens when pipelineId is set, closes on unmount/change.
  useSSE(pipelineId);

  const currentStep = getStoryStep(storyState);

  async function handleLoadDemo() {
    try {
      setError(null);
      const result = await loadScenario('001');
      setPipelineId(result.pipeline_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const isComplete = storyState === 'COMPLETE';

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
          overflow: 'hidden',
        }}
      >
        {/* ── Header bar ─────────────────────────────────────────── */}
        <div
          style={{
            height: 48,
            flexShrink: 0,
            background: '#11111e',
            borderBottom: '1px solid #1e2030',
            display: 'flex',
            alignItems: 'center',
            overflow: 'hidden',
          }}
        >
          {/* Brand */}
          <span
            style={{
              padding: '0 16px',
              fontWeight: 700,
              fontSize: 13,
              color: '#3b82d4',
              letterSpacing: '0.06em',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            Pipeline Autopilot
          </span>

          {/* 12-step progress strip — takes all remaining space */}
          <div style={{ flex: 1, height: '100%', minWidth: 0, overflow: 'hidden' }}>
            <StoryBar />
          </div>

          {/* Load demo button — only before pipeline starts */}
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
                flexShrink: 0,
              }}
            >
              Load Demo
            </button>
          )}

          {/* Pipeline id + streaming indicator */}
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
                flexShrink: 0,
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

        {/* ── Caption bar ────────────────────────────────────────── */}
        <div
          style={{
            height: 28,
            flexShrink: 0,
            background: '#0e0e1a',
            borderBottom: '1px solid #1e2030',
            display: 'flex',
            alignItems: 'center',
            paddingLeft: 16,
            paddingRight: 16,
            gap: 8,
          }}
        >
          {/* Phase dot */}
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: storyState === 'COMPLETE' ? '#22c55e'
                        : storyState === 'FAILURE_PROPAGATING' ? '#ef4444'
                        : storyState === 'HEALTHY' ? '#22c55e'
                        : '#3b82d4',
              display: 'inline-block',
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: 12,
              color: '#8b949e',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {currentStep.caption}
          </span>
        </div>

        {/* ── Main area ──────────────────────────────────────────── */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            overflow: 'hidden',
            minHeight: 0,
          }}
        >
          {/* Canvas column */}
          <div
            style={{
              flex: 1,
              overflow: 'hidden',
              position: 'relative',
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* React Flow canvas — takes all remaining space */}
            <div style={{ flex: 1, overflow: 'hidden', position: 'relative', minHeight: 0 }}>
              <ReactFlowProvider>
                <SystemCanvas />
              </ReactFlowProvider>
              {/* CounterfactualSplit: overlays the canvas bottom when visible */}
              <CounterfactualSplit />
            </div>
          </div>

          {/* Evidence panel — right sidebar, internal scroll */}
          {!isComplete && <EvidencePanel />}

          {/* Recovery report — compact right panel at COMPLETE */}
          {isComplete && recoveryReport && (
            <div
              style={{
                width: 320,
                minWidth: 320,
                maxWidth: 320,
                height: '100%',
                overflowY: 'auto',
                overflowX: 'hidden',
                background: '#11111e',
                borderLeft: '1px solid #1e2030',
                flexShrink: 0,
                scrollbarWidth: 'thin',
                scrollbarColor: '#2a2a4a #11111e',
              }}
            >
              <div style={{ padding: '12px 12px' }}>
                <RecoveryReport />
              </div>
            </div>
          )}
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
      </div>
    </>
  );
}
