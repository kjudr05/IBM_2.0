/**
 * pipelineStore unit tests.
 *
 * Covers:
 *  - initial state shape
 *  - setStoryState action
 *  - setEvidenceForAgent merges correctly
 *  - setCausalChain / setProposedFix / setValidationResult
 *  - setError / setIsStreaming
 *  - reset returns to initial state
 *  - setPipelineId
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { usePipelineStore } from './pipelineStore';

// Reset the store before each test so tests don't bleed into each other.
beforeEach(() => {
  usePipelineStore.getState().reset();
});

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

describe('pipelineStore initial state', () => {
  it('starts in HEALTHY story state', () => {
    expect(usePipelineStore.getState().storyState).toBe('HEALTHY');
  });

  it('has no pipeline ID', () => {
    expect(usePipelineStore.getState().pipelineId).toBeNull();
  });

  it('has empty evidence map', () => {
    expect(usePipelineStore.getState().evidenceByAgent).toEqual({});
  });

  it('has null causal chain', () => {
    expect(usePipelineStore.getState().causalChain).toBeNull();
  });

  it('has null proposed fix', () => {
    expect(usePipelineStore.getState().proposedFix).toBeNull();
  });

  it('is not streaming', () => {
    expect(usePipelineStore.getState().isStreaming).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Story state
// ---------------------------------------------------------------------------

describe('setStoryState', () => {
  it('updates storyState', () => {
    usePipelineStore.getState().setStoryState('AGENTS_ACTIVATING');
    expect(usePipelineStore.getState().storyState).toBe('AGENTS_ACTIVATING');
  });
});

// ---------------------------------------------------------------------------
// Pipeline ID
// ---------------------------------------------------------------------------

describe('setPipelineId', () => {
  it('stores the pipeline ID', () => {
    usePipelineStore.getState().setPipelineId('pipe-123');
    expect(usePipelineStore.getState().pipelineId).toBe('pipe-123');
  });
});

// ---------------------------------------------------------------------------
// Evidence merging
// ---------------------------------------------------------------------------

describe('setEvidenceForAgent', () => {
  it('inserts a new agent entry', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setEvidenceForAgent('log_investigator', { evidence_type: 'failure' } as any);
    expect(usePipelineStore.getState().evidenceByAgent['log_investigator']).toMatchObject({ evidence_type: 'failure' });
  });

  it('merges multiple agents without losing earlier entries', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setEvidenceForAgent('agent_a', { evidence_type: 'change' } as any);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setEvidenceForAgent('agent_b', { evidence_type: 'test' } as any);
    const ev = usePipelineStore.getState().evidenceByAgent;
    expect(ev['agent_a']).toMatchObject({ evidence_type: 'change' });
    expect(ev['agent_b']).toMatchObject({ evidence_type: 'test' });
  });

  it('overwrites existing entry for same agent', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setEvidenceForAgent('agent_a', { evidence_type: 'change', summary: 'first' } as any);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setEvidenceForAgent('agent_a', { evidence_type: 'change', summary: 'second' } as any);
    expect(usePipelineStore.getState().evidenceByAgent['agent_a']).toMatchObject({ summary: 'second' });
  });
});

// ---------------------------------------------------------------------------
// Causal chain
// ---------------------------------------------------------------------------

describe('setCausalChain', () => {
  it('stores the causal chain', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setCausalChain({ chain_id: 'c1', pipeline_id: 'p1' } as any);
    expect(usePipelineStore.getState().causalChain?.chain_id).toBe('c1');
  });
});

// ---------------------------------------------------------------------------
// Proposed fix
// ---------------------------------------------------------------------------

describe('setProposedFix', () => {
  it('stores the fix proposal', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setProposedFix({ fix_id: 'fix-1' } as any);
    expect(usePipelineStore.getState().proposedFix?.fix_id).toBe('fix-1');
  });
});

// ---------------------------------------------------------------------------
// Validation result
// ---------------------------------------------------------------------------

describe('setValidationResult', () => {
  it('stores the validation result', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    usePipelineStore.getState().setValidationResult({ validation_id: 'v-1', status: 'PASSED' } as any);
    expect(usePipelineStore.getState().validationResult?.status).toBe('PASSED');
  });
});

// ---------------------------------------------------------------------------
// Error and streaming flags
// ---------------------------------------------------------------------------

describe('setError / setIsStreaming', () => {
  it('sets an error message', () => {
    usePipelineStore.getState().setError('something went wrong');
    expect(usePipelineStore.getState().error).toBe('something went wrong');
  });

  it('clears an error by passing null', () => {
    usePipelineStore.getState().setError('err');
    usePipelineStore.getState().setError(null);
    expect(usePipelineStore.getState().error).toBeNull();
  });

  it('sets isStreaming flag', () => {
    usePipelineStore.getState().setIsStreaming(true);
    expect(usePipelineStore.getState().isStreaming).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// reset
// ---------------------------------------------------------------------------

describe('reset', () => {
  it('restores initial state after modifications', () => {
    usePipelineStore.getState().setPipelineId('pipe-999');
    usePipelineStore.getState().setStoryState('COMPLETE');
    usePipelineStore.getState().setIsStreaming(true);

    usePipelineStore.getState().reset();

    const s = usePipelineStore.getState();
    expect(s.pipelineId).toBeNull();
    expect(s.storyState).toBe('HEALTHY');
    expect(s.isStreaming).toBe(false);
    expect(s.evidenceByAgent).toEqual({});
  });
});
