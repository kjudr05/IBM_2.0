/**
 * Story machine — 12-state enum, metadata, and transition reducer.
 *
 * Task 10: defines the StoryState enum and the StoryStep metadata shape.
 * Task 11: adds transitionStoryState() — a deterministic reducer that maps
 *          (currentState, incomingEvent/state) → next StoryState.
 *
 * The 12 named states match the plan (§5) exactly.
 * State transitions are driven by SSE STATE_TRANSITION events from the backend.
 *
 * Design rules:
 *  - States only advance forward (no going back during a live run).
 *  - If the requested next state is behind the current state, keep current.
 *  - If the requested state is unknown, keep current (no crash).
 *  - COMPLETE is a terminal state — nothing can advance past it.
 */

import type { StoryStateName } from '../types/events';

// ---------------------------------------------------------------------------
// StoryState enum
// ---------------------------------------------------------------------------

export type StoryState =
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

// ---------------------------------------------------------------------------
// Ordered index — used for forward-only advancement
// ---------------------------------------------------------------------------

/** Ordered progression of all 12 states (index = priority). */
export const STORY_STATE_ORDER: StoryState[] = [
  'HEALTHY',
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

/**
 * Return the 0-based index of a state in the ordered progression,
 * or -1 if the state is not recognised.
 */
export function storyStateIndex(state: string): number {
  return STORY_STATE_ORDER.indexOf(state as StoryState);
}

// ---------------------------------------------------------------------------
// Backend-to-frontend state mapping
// ---------------------------------------------------------------------------

/**
 * Map backend StoryStateName values to our frontend StoryState.
 *
 * The backend emits STATE_TRANSITION events whose `state` field uses the
 * same names as StoryStateName (which mirrors StoryState).  This table
 * handles any minor name divergences between plan sections gracefully.
 */
const BACKEND_TO_STORY_STATE: Record<string, StoryState> = {
  HEALTHY:                  'HEALTHY',
  CHANGE_DETECTED:          'CHANGE_DETECTED',
  FAILURE_PROPAGATING:      'FAILURE_PROPAGATING',
  AGENTS_ACTIVATING:        'AGENTS_ACTIVATING',
  EVIDENCE_FLOWING:         'EVIDENCE_FLOWING',
  EVIDENCE_CONVERGING:      'EVIDENCE_CONVERGING',
  ROOT_CAUSE_IDENTIFIED:    'ROOT_CAUSE_IDENTIFIED',
  FIX_PROPOSED:             'FIX_PROPOSED',
  COUNTERFACTUAL_SIMULATING:'COUNTERFACTUAL_SIMULATING',
  COUNTERFACTUAL_SHOWN:     'COUNTERFACTUAL_SHOWN',
  SYSTEM_RECOVERING:        'SYSTEM_RECOVERING',
  COMPLETE:                 'COMPLETE',
  // Allow the backend to use RECOVERED or SYSTEM_RECOVERED as aliases
  RECOVERED:                'COMPLETE',
  SYSTEM_RECOVERED:         'COMPLETE',
};

// ---------------------------------------------------------------------------
// transitionStoryState — deterministic reducer
// ---------------------------------------------------------------------------

/**
 * Advance the story state machine.
 *
 * @param current  The current StoryState held in the Zustand store.
 * @param incoming The state name emitted by the backend SSE event.
 * @returns        The next StoryState (may equal `current` if no advance).
 *
 * Rules:
 *  1. Map the incoming string to a known StoryState.
 *  2. Only advance forward — if the incoming state index ≤ current, keep current.
 *  3. Unknown incoming string → keep current (no crash).
 */
export function transitionStoryState(
  current: StoryState,
  incoming: StoryStateName | string,
): StoryState {
  const mapped = BACKEND_TO_STORY_STATE[incoming];
  if (!mapped) {
    // Unknown state — stay put
    return current;
  }

  const currentIdx = storyStateIndex(current);
  const nextIdx    = storyStateIndex(mapped);

  // Only advance forward
  if (nextIdx > currentIdx) {
    return mapped;
  }

  return current;
}

// ---------------------------------------------------------------------------
// Story step metadata — used by StoryBar (Task 12) and captions (Task 16)
// ---------------------------------------------------------------------------

export interface StoryStep {
  /** The story state this step corresponds to. */
  state: StoryState;
  /** Short label shown in the StoryBar progress strip. */
  label: string;
  /** Non-technical caption shown at the bottom of the canvas. */
  caption: string;
  /** 0-based index in the 12-step sequence. */
  index: number;
}

/** Ordered list of all 12 story steps. */
export const STORY_STEPS: StoryStep[] = [
  {
    state: 'HEALTHY',
    label: 'Healthy',
    caption: 'System is operating normally.',
    index: 0,
  },
  {
    state: 'CHANGE_DETECTED',
    label: 'Change',
    caption: 'A code change has been pushed to the repository.',
    index: 1,
  },
  {
    state: 'FAILURE_PROPAGATING',
    label: 'Failure',
    caption: 'The CI pipeline has failed. Investigating…',
    index: 2,
  },
  {
    state: 'AGENTS_ACTIVATING',
    label: 'Agents',
    caption: 'Investigation agents are activating to gather evidence.',
    index: 3,
  },
  {
    state: 'EVIDENCE_FLOWING',
    label: 'Evidence',
    caption: 'Agents are collecting and transmitting evidence.',
    index: 4,
  },
  {
    state: 'EVIDENCE_CONVERGING',
    label: 'Converging',
    caption: 'All evidence has been collected. Analysing root cause…',
    index: 5,
  },
  {
    state: 'ROOT_CAUSE_IDENTIFIED',
    label: 'Root Cause',
    caption: 'The root cause of the failure has been identified.',
    index: 6,
  },
  {
    state: 'FIX_PROPOSED',
    label: 'Fix',
    caption: 'A fix has been proposed. Running counterfactual simulation…',
    index: 7,
  },
  {
    state: 'COUNTERFACTUAL_SIMULATING',
    label: 'Simulation',
    caption: 'Simulating system state after the fix is applied.',
    index: 8,
  },
  {
    state: 'COUNTERFACTUAL_SHOWN',
    label: 'Preview',
    caption: 'Preview: the system will recover if this fix is applied.',
    index: 9,
  },
  {
    state: 'SYSTEM_RECOVERING',
    label: 'Recovering',
    caption: 'Applying the fix. Services are recovering.',
    index: 10,
  },
  {
    state: 'COMPLETE',
    label: 'Complete',
    caption: 'Recovery complete. Pipeline is healthy again.',
    index: 11,
  },
];

/** Look up the StoryStep for a given StoryState. */
export function getStoryStep(state: StoryState): StoryStep {
  return STORY_STEPS.find((s) => s.state === state) ?? STORY_STEPS[0];
}
