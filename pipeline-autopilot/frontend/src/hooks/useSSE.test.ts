/**
 * useSSE hook unit tests.
 *
 * Strategy: we test the hook by mocking EventSource and verifying that
 * incoming SSE events correctly update the Zustand store.
 *
 * Covers:
 *  1. SSE event parsing — each event type dispatches to the right store action
 *  2. Story-state transition on STATE_TRANSITION event
 *  3. Evidence dispatch on EVIDENCE_ARRIVED
 *  4. Causal chain dispatch on CAUSAL_CHAIN
 *  5. Fix dispatch on FIX_PROPOSED
 *  6. Validation result dispatch on VALIDATION_RESULT
 *  7. Error handling on ERROR event
 *  8. Cleanup / disconnect: EventSource.close is called on unmount
 *  9. Unknown/unexpected event does not crash
 * 10. null pipelineId — no EventSource is opened
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSSE } from './useSSE';
import { usePipelineStore } from '../state/pipelineStore';

// ---------------------------------------------------------------------------
// EventSource mock
// ---------------------------------------------------------------------------

type MockEventSourceInstance = {
  onmessage: ((e: { data: string }) => void) | null;
  onerror:   ((e: Event) => void) | null;
  close:     ReturnType<typeof vi.fn>;
  /** Helper: fire an onmessage with the given JSON payload */
  emit: (payload: object) => void;
};

let mockInstance: MockEventSourceInstance | null = null;

const MockEventSource = vi.fn().mockImplementation((_url: string) => {
  const inst: MockEventSourceInstance = {
    onmessage: null,
    onerror: null,
    close: vi.fn(),
    emit(payload) {
      inst.onmessage?.({ data: JSON.stringify(payload) });
    },
  };
  mockInstance = inst;
  return inst;
});

// Inject the mock before tests run
beforeEach(() => {
  vi.stubGlobal('EventSource', MockEventSource);
  mockInstance = null;
  usePipelineStore.getState().reset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Render the hook with the given pipelineId */
function renderUseSSE(pipelineId: string | null) {
  return renderHook((id: string | null) => useSSE(id), {
    initialProps: pipelineId,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSSE', () => {
  it('opens an EventSource for a non-null pipelineId', () => {
    renderUseSSE('pipe-001');
    expect(MockEventSource).toHaveBeenCalledWith('/api/stream/pipe-001');
  });

  it('does not open an EventSource when pipelineId is null', () => {
    MockEventSource.mockClear();
    renderUseSSE(null);
    expect(MockEventSource).not.toHaveBeenCalled();
  });

  it('sets isStreaming = true when connection opens', () => {
    renderUseSSE('pipe-001');
    expect(usePipelineStore.getState().isStreaming).toBe(true);
  });

  it('STATE_TRANSITION event advances the story state', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.emit({ type: 'STATE_TRANSITION', state: 'AGENTS_ACTIVATING', ts: '2024-01-01T00:00:00Z' });
    });
    expect(usePipelineStore.getState().storyState).toBe('AGENTS_ACTIVATING');
  });

  it('STATE_TRANSITION does not go backward', () => {
    renderUseSSE('pipe-001');
    // Advance to EVIDENCE_FLOWING first
    act(() => {
      mockInstance!.emit({ type: 'STATE_TRANSITION', state: 'EVIDENCE_FLOWING', ts: '' });
    });
    // Now send a backward transition
    act(() => {
      mockInstance!.emit({ type: 'STATE_TRANSITION', state: 'AGENTS_ACTIVATING', ts: '' });
    });
    expect(usePipelineStore.getState().storyState).toBe('EVIDENCE_FLOWING');
  });

  it('EVIDENCE_ARRIVED dispatches evidence to the store', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.emit({
        type: 'EVIDENCE_ARRIVED',
        agent_id: 'log_investigator',
        evidence: { evidence_type: 'failure', summary: 'ImportError' },
        ts: '',
      });
    });
    const ev = usePipelineStore.getState().evidenceByAgent['log_investigator'];
    expect(ev).toMatchObject({ evidence_type: 'failure', summary: 'ImportError' });
  });

  it('CAUSAL_CHAIN event stores the chain', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.emit({
        type: 'CAUSAL_CHAIN',
        chain: { chain_id: 'chain-1', pipeline_id: 'pipe-001', nodes: [], edges: [] },
        ts: '',
      });
    });
    expect(usePipelineStore.getState().causalChain).toMatchObject({ chain_id: 'chain-1' });
  });

  it('FIX_PROPOSED event stores the fix proposal', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.emit({
        type: 'FIX_PROPOSED',
        fix: { fix_id: 'fix-abc', fix_type: 'DEPENDENCY_CHANGE' },
        ts: '',
      });
    });
    expect(usePipelineStore.getState().proposedFix).toMatchObject({ fix_id: 'fix-abc' });
  });

  it('VALIDATION_RESULT event stores the validation result', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.emit({
        type: 'VALIDATION_RESULT',
        result: { validation_id: 'v-1', status: 'PASSED' },
        ts: '',
      });
    });
    expect(usePipelineStore.getState().validationResult).toMatchObject({ status: 'PASSED' });
  });

  it('ERROR event sets the error message and stops streaming', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.emit({ type: 'ERROR', message: 'backend blew up', ts: '' });
    });
    expect(usePipelineStore.getState().error).toBe('backend blew up');
    expect(usePipelineStore.getState().isStreaming).toBe(false);
  });

  it('unknown event type does NOT crash', () => {
    renderUseSSE('pipe-001');
    expect(() => {
      act(() => {
        mockInstance!.emit({ type: 'TOTALLY_UNKNOWN', foo: 'bar', ts: '' });
      });
    }).not.toThrow();
  });

  it('malformed (non-JSON) SSE data does not crash', () => {
    renderUseSSE('pipe-001');
    expect(() => {
      act(() => {
        mockInstance!.onmessage?.({ data: 'this is not json' });
      });
    }).not.toThrow();
  });

  it('EventSource.close is called on unmount (cleanup)', () => {
    const { unmount } = renderUseSSE('pipe-001');
    expect(mockInstance).not.toBeNull();
    unmount();
    expect(mockInstance!.close).toHaveBeenCalled();
  });

  it('EventSource.close is called when pipelineId changes', () => {
    const { rerender } = renderUseSSE('pipe-001');
    const firstInstance = mockInstance;
    rerender('pipe-002');
    // The previous EventSource should have been closed
    expect(firstInstance!.close).toHaveBeenCalled();
    // A new EventSource should have been opened for the new id
    expect(MockEventSource).toHaveBeenLastCalledWith('/api/stream/pipe-002');
  });

  it('onerror handler sets error and stops streaming', () => {
    renderUseSSE('pipe-001');
    act(() => {
      mockInstance!.onerror?.(new Event('error'));
    });
    expect(usePipelineStore.getState().error).toBe('SSE connection error');
    expect(usePipelineStore.getState().isStreaming).toBe(false);
  });

  it('COMPLETE transition closes the EventSource', () => {
    renderUseSSE('pipe-001');
    act(() => {
      // Walk to SYSTEM_RECOVERING first so COMPLETE can advance
      mockInstance!.emit({ type: 'STATE_TRANSITION', state: 'SYSTEM_RECOVERING', ts: '' });
    });
    act(() => {
      mockInstance!.emit({ type: 'STATE_TRANSITION', state: 'COMPLETE', ts: '' });
    });
    // The openSSEStream helper closes the EventSource on COMPLETE
    expect(mockInstance!.close).toHaveBeenCalled();
    expect(usePipelineStore.getState().storyState).toBe('COMPLETE');
  });
});
