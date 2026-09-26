/**
 * Story machine unit tests.
 *
 * Covers:
 *  - transitionStoryState: correct forward transitions
 *  - transitionStoryState: no backward movement
 *  - transitionStoryState: unknown / garbage event does not crash
 *  - storyStateIndex: ordering is correct
 *  - STORY_STEPS metadata is complete and ordered
 */

import { describe, it, expect } from 'vitest';
import {
  transitionStoryState,
  storyStateIndex,
  STORY_STATE_ORDER,
  STORY_STEPS,
  getStoryStep,
} from './storyMachine';
import type { StoryState } from './storyMachine';

// ---------------------------------------------------------------------------
// transitionStoryState
// ---------------------------------------------------------------------------

describe('transitionStoryState', () => {
  it('advances from HEALTHY to CHANGE_DETECTED', () => {
    expect(transitionStoryState('HEALTHY', 'CHANGE_DETECTED')).toBe('CHANGE_DETECTED');
  });

  it('advances from AGENTS_ACTIVATING to EVIDENCE_FLOWING', () => {
    expect(transitionStoryState('AGENTS_ACTIVATING', 'EVIDENCE_FLOWING')).toBe('EVIDENCE_FLOWING');
  });

  it('advances all the way to COMPLETE', () => {
    expect(transitionStoryState('SYSTEM_RECOVERING', 'COMPLETE')).toBe('COMPLETE');
  });

  it('does NOT go backward — returns current state', () => {
    // FAILURE_PROPAGATING (index 2) → CHANGE_DETECTED (index 1) — no regression
    expect(transitionStoryState('FAILURE_PROPAGATING', 'CHANGE_DETECTED')).toBe('FAILURE_PROPAGATING');
  });

  it('does NOT re-enter the same state', () => {
    expect(transitionStoryState('AGENTS_ACTIVATING', 'AGENTS_ACTIVATING')).toBe('AGENTS_ACTIVATING');
  });

  it('returns current state for an unknown incoming string', () => {
    expect(transitionStoryState('HEALTHY', 'NOT_A_REAL_STATE')).toBe('HEALTHY');
  });

  it('returns current state for empty string', () => {
    expect(transitionStoryState('HEALTHY', '')).toBe('HEALTHY');
  });

  it('does not crash on garbage input', () => {
    const result = transitionStoryState('FIX_PROPOSED', '🚨💥invalid');
    expect(result).toBe('FIX_PROPOSED');
  });

  it('maps RECOVERED alias to COMPLETE', () => {
    expect(transitionStoryState('SYSTEM_RECOVERING', 'RECOVERED')).toBe('COMPLETE');
  });

  it('maps SYSTEM_RECOVERED alias to COMPLETE', () => {
    expect(transitionStoryState('SYSTEM_RECOVERING', 'SYSTEM_RECOVERED')).toBe('COMPLETE');
  });

  it('COMPLETE is terminal — nothing advances past it', () => {
    // No state exists after COMPLETE so the only test is that it stays put
    expect(transitionStoryState('COMPLETE', 'COMPLETE')).toBe('COMPLETE');
  });

  it('walks through the full 12-step sequence in order', () => {
    let state: StoryState = 'HEALTHY';
    const expected: StoryState[] = [
      'CHANGE_DETECTED',
      'FAILURE_PROPAGATING',
      'AGENTS_ACTIVATING',
      'EVIDENCE_FLOWING',
      'EVIDENCE_CONVERGING',
      'ROOT_CAUSE_IDENTIFIED',
      'FIX_PROPOSED',
      'COUNTERFACTUAL_SIMULATING',
      'COUNTERFACTUAL_SHOWN',
      'SYSTEM_RECOVERING',
      'COMPLETE',
    ];

    for (const next of expected) {
      state = transitionStoryState(state, next);
      expect(state).toBe(next);
    }
  });
});

// ---------------------------------------------------------------------------
// storyStateIndex
// ---------------------------------------------------------------------------

describe('storyStateIndex', () => {
  it('HEALTHY is index 0', () => {
    expect(storyStateIndex('HEALTHY')).toBe(0);
  });

  it('COMPLETE is the last index', () => {
    expect(storyStateIndex('COMPLETE')).toBe(STORY_STATE_ORDER.length - 1);
  });

  it('returns -1 for an unknown state', () => {
    expect(storyStateIndex('UNKNOWN')).toBe(-1);
  });

  it('every state in STORY_STATE_ORDER has a non-negative index', () => {
    for (const s of STORY_STATE_ORDER) {
      expect(storyStateIndex(s)).toBeGreaterThanOrEqual(0);
    }
  });
});

// ---------------------------------------------------------------------------
// STORY_STEPS metadata
// ---------------------------------------------------------------------------

describe('STORY_STEPS', () => {
  it('has exactly 12 steps', () => {
    expect(STORY_STEPS).toHaveLength(12);
  });

  it('each step has a non-empty label and caption', () => {
    for (const step of STORY_STEPS) {
      expect(step.label.length).toBeGreaterThan(0);
      expect(step.caption.length).toBeGreaterThan(0);
    }
  });

  it('step indices are 0-based and sequential', () => {
    STORY_STEPS.forEach((step, i) => {
      expect(step.index).toBe(i);
    });
  });

  it('getStoryStep returns correct step for each state', () => {
    for (const s of STORY_STATE_ORDER) {
      const step = getStoryStep(s as StoryState);
      expect(step.state).toBe(s);
    }
  });
});
