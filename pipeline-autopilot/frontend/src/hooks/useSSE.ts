/**
 * useSSE — hook that opens an SSE connection and dispatches events to pipelineStore.
 *
 * Task 10: stub that exports the signature for TypeScript compilation.
 * Task 11: full implementation wiring SSE events into usePipelineStore actions.
 *
 * Opens GET /api/stream/{pipelineId} via the low-level openSSEStream utility.
 * Parses each typed SSE event and calls the corresponding store action.
 * Cleans up (closes the EventSource) on unmount or when pipelineId changes.
 */

import { useEffect } from 'react';
import { openSSEStream } from '../api/sse';
import { usePipelineStore } from '../state/pipelineStore';
import { transitionStoryState } from '../state/storyMachine';
import type { SSEEvent, StoryStateName } from '../types/events';
import type { AnyEvidence } from '../types/evidence';
import type { CausalChain } from '../types/causal';
import type { FixProposal, ValidationResult } from '../types/fix';

export function useSSE(pipelineId: string | null): void {
  const setStoryState  = usePipelineStore((s) => s.setStoryState);
  const setEvidenceForAgent = usePipelineStore((s) => s.setEvidenceForAgent);
  const setCausalChain = usePipelineStore((s) => s.setCausalChain);
  const setProposedFix = usePipelineStore((s) => s.setProposedFix);
  const setValidationResult = usePipelineStore((s) => s.setValidationResult);
  const setError       = usePipelineStore((s) => s.setError);
  const setIsStreaming = usePipelineStore((s) => s.setIsStreaming);
  const getState       = usePipelineStore.getState;

  useEffect(() => {
    if (!pipelineId) return;

    setIsStreaming(true);

    function handleEvent(event: SSEEvent): void {
      switch (event.type) {
        case 'STATE_TRANSITION': {
          const next = transitionStoryState(
            getState().storyState,
            event.state as StoryStateName,
          );
          setStoryState(next);
          break;
        }

        case 'EVIDENCE_ARRIVED': {
          // Cast through unknown — backend sends a typed evidence blob
          setEvidenceForAgent(
            event.agent_id,
            event.evidence as unknown as AnyEvidence,
          );
          break;
        }

        case 'CAUSAL_CHAIN': {
          setCausalChain(event.chain as unknown as CausalChain);
          break;
        }

        case 'FIX_PROPOSED': {
          setProposedFix(event.fix as unknown as FixProposal);
          break;
        }

        case 'VALIDATION_RESULT': {
          setValidationResult(event.result as unknown as ValidationResult);
          break;
        }

        case 'REPORT_READY': {
          // report_id is available; the full report can be fetched via
          // GET /api/report/{report_id}.  Store sets nothing for now —
          // App.tsx can fetch it when storyState reaches COMPLETE.
          break;
        }

        case 'ERROR': {
          setError(event.message);
          setIsStreaming(false);
          break;
        }

        default: {
          // Unknown event type — ignore safely (no crash)
          break;
        }
      }
    }

    function handleError(_err: Event): void {
      setError('SSE connection error');
      setIsStreaming(false);
    }

    function handleComplete(): void {
      setIsStreaming(false);
    }

    const cleanup = openSSEStream(
      pipelineId,
      handleEvent,
      handleError,
      handleComplete,
    );

    return () => {
      cleanup();
      setIsStreaming(false);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelineId]);
}
