/**
 * SSE connection utilities.
 *
 * Task 10: exports the SSEEvent union type and a low-level openSSEStream
 * helper that callers can use to receive typed events from the backend.
 *
 * Task 11: useSSE hook will be implemented here, consuming these utilities
 * and dispatching events into usePipelineStore.
 */

export type { SSEEvent, SSEStateTransitionEvent, SSEEvidenceArrivedEvent, SSECausalChainEvent, SSEFixProposedEvent, SSEValidationResultEvent, SSEReportReadyEvent, SSEErrorEvent } from '../types/events';

// ---------------------------------------------------------------------------
// Low-level SSE stream opener
// ---------------------------------------------------------------------------

/**
 * Open an SSE stream for the given pipeline_id.
 *
 * Calls `onEvent` for each parsed JSON event and `onError` if the stream
 * fails or closes unexpectedly.  Returns a cleanup function that closes
 * the EventSource.
 *
 * Note: Task 11 will call this from the useSSE hook and dispatch events
 * into usePipelineStore.
 */
export function openSSEStream(
  pipelineId: string,
  onEvent: (event: import('../types/events').SSEEvent) => void,
  onError?: (err: Event) => void,
  onComplete?: () => void,
): () => void {
  const source = new EventSource(`/api/stream/${pipelineId}`);

  source.onmessage = (e: MessageEvent<string>) => {
    try {
      const parsed = JSON.parse(e.data) as import('../types/events').SSEEvent;
      onEvent(parsed);
      // Close the connection once the story completes
      if (parsed.type === 'STATE_TRANSITION' && parsed.state === 'COMPLETE') {
        source.close();
        onComplete?.();
      }
      if (parsed.type === 'ERROR') {
        source.close();
        onComplete?.();
      }
    } catch {
      // Non-JSON data line — ignore
    }
  };

  source.onerror = (e) => {
    onError?.(e);
    source.close();
  };

  return () => source.close();
}
