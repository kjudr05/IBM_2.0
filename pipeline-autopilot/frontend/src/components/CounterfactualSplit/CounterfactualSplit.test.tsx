/**
 * Task 14 — CounterfactualSplit unit tests.
 *
 * Covers:
 *  Visibility:
 *    - hidden when counterfactual is null
 *    - hidden when counterfactual is set but storyState is wrong
 *    - visible when counterfactual is set AND storyState is COUNTERFACTUAL_SHOWN
 *    - visible during COUNTERFACTUAL_SIMULATING
 *    - visible during SYSTEM_RECOVERING
 *    - visible during COMPLETE
 *
 *  BEFORE state rendering:
 *    - "before" panel is present
 *    - "Before Fix" label appears
 *    - failed nodes appear in before panel with FAILED health
 *
 *  AFTER state rendering:
 *    - "after" panel is present
 *    - "After Fix" label appears
 *    - recovered nodes appear in after panel with HEALTHY health
 *
 *  Counterfactual data:
 *    - narrative text is rendered
 *    - changed_nodes count badge appears
 *    - title "Counterfactual Analysis" is present
 *    - arrow divider is rendered
 *
 *  Failed → Healthy node transition:
 *    - before grid contains FAILED nodes
 *    - after grid contains HEALTHY nodes for same node IDs
 *    - node ids referenced in changed_nodes appear in both panels
 *    - health data-health attribute matches the state for each panel
 *
 * Strategy:
 *  - Uses @testing-library/react
 *  - Zustand store reset before each test
 *  - framer-motion is mocked (removes animation from jsdom)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { usePipelineStore } from '../../state/pipelineStore';
import type { CounterfactualResult } from '../../types/fix';

// ---------------------------------------------------------------------------
// Mock framer-motion — removes animations from jsdom.
// vi.mock factories are hoisted, so we cannot use ESM imports inside them.
// Instead we use a simpler passthrough: motion.div → plain <div>, etc.
// ---------------------------------------------------------------------------

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion');
  // Replace animated components with plain DOM equivalents that pass all
  // non-animation props through. This avoids the `require()` TS error while
  // keeping the mock compatible with jsdom.
  const makePlain =
    (tag: string) =>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ({ children, initial: _i, animate: _a, exit: _x, transition: _t, whileHover: _w, layout: _l, ...rest }: any) =>
      // @ts-expect-error dynamic tag
      actual.m ? null : <>{children}</> || (({ tag, rest, children }) => <div {...rest}>{children}</div>)({ tag, rest, children });

  void makePlain; // suppress unused warning — not used below

  return {
    // AnimatePresence just renders children directly
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    // motion.div / motion.span / etc. → strip animation props, pass rest to native element
    motion: new Proxy({} as Record<string, React.FC>, {
      get: (_obj, tag: string) =>
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        function MotionEl({ children, initial: _i, animate: _a, exit: _x, transition: _t, layout: _l, ...rest }: any) {
          const Tag = tag as keyof JSX.IntrinsicElements;
          return <Tag {...rest}>{children}</Tag>;
        },
    }),
  };
});

import { CounterfactualSplit } from './CounterfactualSplit';

// ---------------------------------------------------------------------------
// Reset store before each test
// ---------------------------------------------------------------------------

beforeEach(() => {
  usePipelineStore.getState().reset();
});

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

function makeCounterfactual(
  overrides: Partial<CounterfactualResult> = {},
): CounterfactualResult {
  return {
    pipeline_id: 'pipeline-test-001',
    fix_id: 'fix-001',
    before_state: {
      nodes: {
        payments_service: 'FAILED',
        auth_service: 'FAILED',
        api_gateway: 'DEGRADED',
      },
    },
    after_state: {
      nodes: {
        payments_service: 'HEALTHY',
        auth_service: 'HEALTHY',
        api_gateway: 'HEALTHY',
      },
    },
    changed_nodes: ['payments_service', 'auth_service', 'api_gateway'],
    narrative:
      'If the dependency is pinned to v2.3.1, all 3 failing services will recover.',
    ...overrides,
  };
}

/** Set counterfactual and story state together */
function setup(
  storyState: Parameters<ReturnType<typeof usePipelineStore.getState>['setStoryState']>[0],
  cfOverrides: Partial<CounterfactualResult> = {},
) {
  usePipelineStore.getState().setStoryState(storyState);
  usePipelineStore.getState().setCounterfactual(makeCounterfactual(cfOverrides));
}

// ===========================================================================
// Visibility
// ===========================================================================

describe('CounterfactualSplit — visibility', () => {
  it('is hidden when counterfactual is null', () => {
    usePipelineStore.getState().setStoryState('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.queryByTestId('counterfactual-split')).toBeNull();
  });

  it('is hidden when counterfactual is set but storyState is HEALTHY', () => {
    usePipelineStore.getState().setCounterfactual(makeCounterfactual());
    usePipelineStore.getState().setStoryState('HEALTHY');
    render(<CounterfactualSplit />);
    expect(screen.queryByTestId('counterfactual-split')).toBeNull();
  });

  it('is hidden when storyState is FIX_PROPOSED (before simulation)', () => {
    setup('FIX_PROPOSED');
    render(<CounterfactualSplit />);
    expect(screen.queryByTestId('counterfactual-split')).toBeNull();
  });

  it('is visible when storyState is COUNTERFACTUAL_SIMULATING', () => {
    setup('COUNTERFACTUAL_SIMULATING');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('counterfactual-split')).toBeDefined();
  });

  it('is visible when storyState is COUNTERFACTUAL_SHOWN', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('counterfactual-split')).toBeDefined();
  });

  it('is visible when storyState is SYSTEM_RECOVERING', () => {
    setup('SYSTEM_RECOVERING');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('counterfactual-split')).toBeDefined();
  });

  it('is visible when storyState is COMPLETE', () => {
    setup('COMPLETE');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('counterfactual-split')).toBeDefined();
  });
});

// ===========================================================================
// BEFORE state rendering
// ===========================================================================

describe('CounterfactualSplit — BEFORE state', () => {
  it('renders the before panel', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-before-panel')).toBeDefined();
  });

  it('renders "Before Fix" label', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByText('Before Fix')).toBeDefined();
  });

  it('renders node grid for before side', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-node-grid-before')).toBeDefined();
  });

  it('before panel contains FAILED node cards', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED', auth_service: 'FAILED' } },
    });
    render(<CounterfactualSplit />);
    const beforePanel = screen.getByTestId('cf-before-panel');
    // At least one card has data-health="FAILED"
    const failedCards = beforePanel.querySelectorAll('[data-health="FAILED"]');
    expect(failedCards.length).toBeGreaterThan(0);
  });

  it('before panel shows health pills with FAILED text', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED' } },
      after_state: { nodes: { payments_service: 'HEALTHY' } },
      changed_nodes: ['payments_service'],
    });
    render(<CounterfactualSplit />);
    const beforePanel = screen.getByTestId('cf-before-panel');
    expect(beforePanel.textContent).toContain('FAILED');
  });

  it('before node card has correct data-node-id attribute', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED' } },
      after_state: { nodes: { payments_service: 'HEALTHY' } },
      changed_nodes: ['payments_service'],
    });
    render(<CounterfactualSplit />);
    const beforeGrid = screen.getByTestId('cf-node-grid-before');
    const card = beforeGrid.querySelector('[data-node-id="payments_service"]');
    expect(card).not.toBeNull();
  });
});

// ===========================================================================
// AFTER state rendering
// ===========================================================================

describe('CounterfactualSplit — AFTER state', () => {
  it('renders the after panel', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-after-panel')).toBeDefined();
  });

  it('renders "After Fix" label', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByText('After Fix')).toBeDefined();
  });

  it('renders node grid for after side', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-node-grid-after')).toBeDefined();
  });

  it('after panel contains HEALTHY node cards', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      after_state: { nodes: { payments_service: 'HEALTHY', auth_service: 'HEALTHY' } },
    });
    render(<CounterfactualSplit />);
    const afterPanel = screen.getByTestId('cf-after-panel');
    const healthyCards = afterPanel.querySelectorAll('[data-health="HEALTHY"]');
    expect(healthyCards.length).toBeGreaterThan(0);
  });

  it('after panel shows health pills with HEALTHY text', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED' } },
      after_state: { nodes: { payments_service: 'HEALTHY' } },
      changed_nodes: ['payments_service'],
    });
    render(<CounterfactualSplit />);
    const afterPanel = screen.getByTestId('cf-after-panel');
    expect(afterPanel.textContent).toContain('HEALTHY');
  });

  it('after node card has correct data-node-id attribute', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED' } },
      after_state: { nodes: { payments_service: 'HEALTHY' } },
      changed_nodes: ['payments_service'],
    });
    render(<CounterfactualSplit />);
    const afterGrid = screen.getByTestId('cf-node-grid-after');
    const card = afterGrid.querySelector('[data-node-id="payments_service"]');
    expect(card).not.toBeNull();
  });
});

// ===========================================================================
// Failed → Healthy transition
// ===========================================================================

describe('CounterfactualSplit — FAILED → HEALTHY node transition', () => {
  it('same node ID appears FAILED in before and HEALTHY in after', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED' } },
      after_state: { nodes: { payments_service: 'HEALTHY' } },
      changed_nodes: ['payments_service'],
    });
    render(<CounterfactualSplit />);

    const beforeCard = screen
      .getByTestId('cf-node-grid-before')
      .querySelector('[data-node-id="payments_service"]');
    const afterCard = screen
      .getByTestId('cf-node-grid-after')
      .querySelector('[data-node-id="payments_service"]');

    expect(beforeCard?.getAttribute('data-health')).toBe('FAILED');
    expect(afterCard?.getAttribute('data-health')).toBe('HEALTHY');
  });

  it('all changed_nodes appear in after panel with HEALTHY status', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    const afterGrid = screen.getByTestId('cf-node-grid-after');
    const healthyCards = afterGrid.querySelectorAll('[data-health="HEALTHY"]');
    // All 3 changed_nodes are HEALTHY
    expect(healthyCards.length).toBe(3);
  });

  it('nodes DEGRADED before can become HEALTHY after', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { api_gateway: 'DEGRADED' } },
      after_state: { nodes: { api_gateway: 'HEALTHY' } },
      changed_nodes: ['api_gateway'],
    });
    render(<CounterfactualSplit />);

    const beforeCard = screen
      .getByTestId('cf-node-grid-before')
      .querySelector('[data-node-id="api_gateway"]');
    const afterCard = screen
      .getByTestId('cf-node-grid-after')
      .querySelector('[data-node-id="api_gateway"]');

    expect(beforeCard?.getAttribute('data-health')).toBe('DEGRADED');
    expect(afterCard?.getAttribute('data-health')).toBe('HEALTHY');
  });

  it('unchanged nodes (not in changed_nodes) keep their before health in after', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { stable_service: 'HEALTHY', broken_service: 'FAILED' } },
      after_state: { nodes: { stable_service: 'HEALTHY', broken_service: 'HEALTHY' } },
      changed_nodes: ['broken_service'], // stable_service not in changed list
    });
    render(<CounterfactualSplit />);
    const afterGrid = screen.getByTestId('cf-node-grid-after');
    const stableCard = afterGrid.querySelector('[data-node-id="stable_service"]');
    expect(stableCard?.getAttribute('data-health')).toBe('HEALTHY');
  });
});

// ===========================================================================
// Counterfactual data rendering
// ===========================================================================

describe('CounterfactualSplit — counterfactual data', () => {
  it('renders the narrative text', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      narrative: 'If the dependency is pinned, the pipeline will recover.',
    });
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-narrative').textContent).toContain(
      'If the dependency is pinned, the pipeline will recover.',
    );
  });

  it('renders the title "Counterfactual Analysis"', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-title').textContent).toContain('Counterfactual Analysis');
  });

  it('renders changed count badge when changed_nodes has items', () => {
    setup('COUNTERFACTUAL_SHOWN', { changed_nodes: ['payments_service', 'auth_service'] });
    render(<CounterfactualSplit />);
    const badge = screen.getByTestId('cf-changed-count');
    expect(badge.textContent).toContain('2');
  });

  it('does not render changed count badge when changed_nodes is empty', () => {
    setup('COUNTERFACTUAL_SHOWN', { changed_nodes: [] });
    render(<CounterfactualSplit />);
    expect(screen.queryByTestId('cf-changed-count')).toBeNull();
  });

  it('renders the divider arrow between before and after panels', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-arrow')).toBeDefined();
  });

  it('singular badge text when exactly 1 node recovers', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      before_state: { nodes: { payments_service: 'FAILED' } },
      after_state: { nodes: { payments_service: 'HEALTHY' } },
      changed_nodes: ['payments_service'],
    });
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-changed-count').textContent).toContain('1 node recover');
  });

  it('plural badge text when more than 1 node recovers', () => {
    setup('COUNTERFACTUAL_SHOWN', {
      changed_nodes: ['payments_service', 'auth_service', 'api_gateway'],
    });
    render(<CounterfactualSplit />);
    expect(screen.getByTestId('cf-changed-count').textContent).toContain('3 nodes recover');
  });
});

// ===========================================================================
// Integration — component visibility / integration
// ===========================================================================

describe('CounterfactualSplit — component integration', () => {
  it('renders null / nothing without mounting anything when no data', () => {
    const { container } = render(<CounterfactualSplit />);
    // counterfactual is null from reset, so nothing rendered
    expect(container.firstChild).toBeNull();
  });

  it('complete render: before + after panels both contain node cards', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    const allCards = screen.getAllByTestId('cf-node-card');
    // 3 nodes in before + 3 in after = 6 total
    expect(allCards.length).toBe(6);
  });

  it('displays the "Before Fix" column header with correct label', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    // The label text is rendered inside cf-before-panel
    const beforePanel = screen.getByTestId('cf-before-panel');
    expect(beforePanel.textContent).toContain('Before Fix');
  });

  it('displays the "After Fix" column header with correct label', () => {
    setup('COUNTERFACTUAL_SHOWN');
    render(<CounterfactualSplit />);
    const afterPanel = screen.getByTestId('cf-after-panel');
    expect(afterPanel.textContent).toContain('After Fix');
  });

  it('hides after counterfactual is removed from store', () => {
    setup('COUNTERFACTUAL_SHOWN');
    const { rerender } = render(<CounterfactualSplit />);
    expect(screen.getByTestId('counterfactual-split')).toBeDefined();

    act(() => { usePipelineStore.getState().reset(); });
    rerender(<CounterfactualSplit />);
    expect(screen.queryByTestId('counterfactual-split')).toBeNull();
  });

  it('appears when storyState advances to COUNTERFACTUAL_SIMULATING', () => {
    act(() => {
      usePipelineStore.getState().setCounterfactual(makeCounterfactual());
      usePipelineStore.getState().setStoryState('FIX_PROPOSED'); // not yet visible
    });
    const { rerender } = render(<CounterfactualSplit />);
    expect(screen.queryByTestId('counterfactual-split')).toBeNull();

    act(() => { usePipelineStore.getState().setStoryState('COUNTERFACTUAL_SIMULATING'); });
    rerender(<CounterfactualSplit />);
    expect(screen.getByTestId('counterfactual-split')).toBeDefined();
  });
});
