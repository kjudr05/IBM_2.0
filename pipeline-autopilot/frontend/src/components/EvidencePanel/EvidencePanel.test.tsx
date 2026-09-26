/**
 * Task 13 — EvidencePanel unit tests.
 *
 * Covers:
 *  EvidencePanel:
 *    - hidden (data-visible="false") when no causal chain
 *    - visible (data-visible="true") when causal chain arrives
 *    - width=0 (hidden) when no causal chain
 *    - renders root-cause headline when causal chain is present
 *    - shows plain-language narrative
 *    - shows root-cause label prominently
 *    - shows confidence percentage
 *
 *  CausalChainView:
 *    - renders all chain nodes
 *    - root-cause node has data-root="true"
 *    - non-root nodes have data-root="false"
 *    - renders node labels
 *    - renders edge relation connectors
 *    - renders edge explanations
 *
 *  EvidenceCard:
 *    - renders evidence summary
 *    - renders type badge
 *    - renders confidence bar
 *    - Inspect button appears when onInspect is provided
 *    - active prop toggles data-active attribute
 *
 *  TechnicalDrill:
 *    - renders for failure evidence type (stack trace section)
 *    - renders for test evidence type (failed tests section)
 *    - expandable sections start collapsed by default
 *    - toggle opens a section
 *    - known fix shown for historical evidence
 *
 *  Integration (EvidencePanel + TechnicalDrill inline):
 *    - clicking Inspect shows TechnicalDrill for that evidence card
 *    - clicking Inspect again hides TechnicalDrill (toggle)
 *    - only one TechnicalDrill shown at a time
 *
 * Strategy:
 *  - Uses @testing-library/react
 *  - Zustand store reset before each test
 *  - Components tested in isolation where possible
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { usePipelineStore } from '../../state/pipelineStore';

import { EvidencePanel } from './EvidencePanel';
import { CausalChainView } from './CausalChain';
import { EvidenceCard }    from './EvidenceCard';
import { TechnicalDrill }  from './TechnicalDrill';

import type { CausalChain } from '../../types/causal';
import type {
  FailureEvidence,
  TestRunEvidence,
  HistoricalEvidence,
  AnyEvidence,
} from '../../types/evidence';

// ---------------------------------------------------------------------------
// Reset store before each test
// ---------------------------------------------------------------------------

beforeEach(() => {
  usePipelineStore.getState().reset();
});

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

function makeCausalChain(overrides: Partial<CausalChain> = {}): CausalChain {
  return {
    chain_id: 'chain-001',
    pipeline_id: 'pipeline-abc-12345678',
    nodes: [
      {
        node_id: 'n1',
        node_type: 'CHANGE',
        label: 'Dependency upgrade',
        description: 'lodash was upgraded from 4.17.19 to 4.17.21',
        evidence_ids: ['ev1'],
        confidence: 0.9,
      },
      {
        node_id: 'n2',
        node_type: 'ROOT_CAUSE',
        label: 'Breaking API change',
        description: 'The new lodash version removed _.flattenDeep',
        evidence_ids: ['ev1', 'ev2'],
        confidence: 0.87,
      },
      {
        node_id: 'n3',
        node_type: 'FAILURE',
        label: 'Build step failed',
        description: 'Webpack build crashed due to unresolved import',
        evidence_ids: ['ev2'],
        confidence: 0.95,
      },
    ],
    edges: [
      {
        edge_id: 'e1',
        source_node_id: 'n1',
        target_node_id: 'n2',
        relation: 'caused',
        explanation: 'The upgrade introduced a breaking change.',
      },
      {
        edge_id: 'e2',
        source_node_id: 'n2',
        target_node_id: 'n3',
        relation: 'triggered',
        explanation: 'The missing symbol triggered a compile error.',
      },
    ],
    root_cause_node_id: 'n2',
    narrative:
      'A routine dependency upgrade removed a function that the build process relied on. This caused the CI pipeline to fail during the build step.',
    confidence: 0.87,
    builder_version: '1.0.0',
    ...overrides,
  };
}

function makeFailureEvidence(overrides: Partial<FailureEvidence> = {}): FailureEvidence {
  return {
    evidence_id: 'ev-fail-001',
    pipeline_id: 'pipeline-abc-12345678',
    evidence_type: 'failure',
    source: { agent_id: 'log_investigator', input_file: null, provider: null },
    created_at: '2024-01-15T10:00:00Z',
    confidence: 0.95,
    summary: 'Build step crashed with TypeError: _.flattenDeep is not a function',
    error_class: 'TypeError',
    error_message: '_.flattenDeep is not a function',
    stack_trace: ['at build.js:42', 'at webpack.js:101'],
    affected_stage: 'build',
    failure_timestamp: '2024-01-15T10:00:00Z',
    severity: 'critical',
    log_excerpt: 'ERROR TypeError: _.flattenDeep is not a function\n  at build.js:42',
    file_path: 'build.js',
    line_number: 42,
    ...overrides,
  };
}

function makeTestEvidence(overrides: Partial<TestRunEvidence> = {}): TestRunEvidence {
  return {
    evidence_id: 'ev-test-001',
    pipeline_id: 'pipeline-abc-12345678',
    evidence_type: 'test',
    source: { agent_id: 'test_investigator', input_file: null, provider: null },
    created_at: '2024-01-15T10:01:00Z',
    confidence: 0.88,
    summary: '3 tests failed due to lodash API changes',
    failed_tests: [
      {
        name: 'testFlattenArray',
        class_name: 'ArrayHelperTest',
        failure_message: 'TypeError: _.flattenDeep is not a function',
        duration_ms: 12,
      },
    ],
    flaky_tests: [],
    regression_tests: ['testFlattenArray'],
    total_run: 120,
    total_failed: 3,
    total_passed: 117,
    total_skipped: 0,
    ...overrides,
  };
}

function makeHistoricalEvidence(overrides: Partial<HistoricalEvidence> = {}): HistoricalEvidence {
  return {
    evidence_id: 'ev-hist-001',
    pipeline_id: 'pipeline-abc-12345678',
    evidence_type: 'historical',
    source: { agent_id: 'historical_investigator', input_file: null, provider: null },
    created_at: '2024-01-15T10:02:00Z',
    confidence: 0.75,
    summary: 'This type of lodash breakage has been seen 2 times before',
    similar_failures: [
      {
        run_id: 'run-prev-001',
        date: '2023-11-01T00:00:00Z',
        root_cause: 'lodash version mismatch',
        fix_applied: 'pinned lodash version',
        similarity_score: 0.92,
      },
    ],
    recurrence_count: 2,
    last_seen: '2023-11-01T00:00:00Z',
    known_fix: 'Pin lodash to the previous version or update code to use new API.',
    ...overrides,
  };
}

// ===========================================================================
// EvidencePanel — visibility
// ===========================================================================

describe('EvidencePanel — visibility', () => {
  it('has data-visible="false" when no causal chain', () => {
    render(<EvidencePanel />);
    expect(screen.getByTestId('evidence-panel').getAttribute('data-visible')).toBe('false');
  });

  it('has data-visible="true" when causal chain is set', () => {
    usePipelineStore.getState().setCausalChain(makeCausalChain());
    render(<EvidencePanel />);
    expect(screen.getByTestId('evidence-panel').getAttribute('data-visible')).toBe('true');
  });

  it('does NOT render the root-cause headline when no causal chain', () => {
    render(<EvidencePanel />);
    expect(screen.queryByTestId('root-cause-headline')).toBeNull();
  });

  it('renders the root-cause headline when causal chain is present', () => {
    usePipelineStore.getState().setCausalChain(makeCausalChain());
    render(<EvidencePanel />);
    expect(screen.getByTestId('root-cause-headline')).toBeDefined();
  });
});

// ===========================================================================
// EvidencePanel — plain-language root cause (Level 2)
// ===========================================================================

describe('EvidencePanel — plain-language root cause', () => {
  it('shows the narrative text', () => {
    const chain = makeCausalChain();
    usePipelineStore.getState().setCausalChain(chain);
    render(<EvidencePanel />);
    expect(screen.getByTestId('root-cause-narrative').textContent).toBe(chain.narrative);
  });

  it('shows the root-cause node label prominently', () => {
    const chain = makeCausalChain();
    usePipelineStore.getState().setCausalChain(chain);
    render(<EvidencePanel />);
    expect(screen.getByTestId('root-cause-label').textContent).toBe('Breaking API change');
  });

  it('shows the confidence percentage', () => {
    const chain = makeCausalChain();
    usePipelineStore.getState().setCausalChain(chain);
    render(<EvidencePanel />);
    expect(screen.getByTestId('root-cause-confidence-pct').textContent).toContain('87%');
  });

  it('shows "Root Cause Identified" status pill', () => {
    usePipelineStore.getState().setCausalChain(makeCausalChain());
    render(<EvidencePanel />);
    expect(screen.getByTestId('root-cause-status-pill').textContent).toContain('Root Cause Identified');
  });

  it('shows the root-cause description', () => {
    usePipelineStore.getState().setCausalChain(makeCausalChain());
    render(<EvidencePanel />);
    expect(screen.getByTestId('root-cause-description').textContent).toContain('_.flattenDeep');
  });
});

// ===========================================================================
// CausalChainView — causal chain rendering
// ===========================================================================

describe('CausalChainView — causal chain rendering', () => {
  it('renders all chain nodes', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('causal-node-n1')).toBeDefined();
    expect(screen.getByTestId('causal-node-n2')).toBeDefined();
    expect(screen.getByTestId('causal-node-n3')).toBeDefined();
  });

  it('marks the root-cause node with data-root="true"', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('causal-node-n2').getAttribute('data-root')).toBe('true');
  });

  it('marks non-root nodes with data-root="false"', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('causal-node-n1').getAttribute('data-root')).toBe('false');
    expect(screen.getByTestId('causal-node-n3').getAttribute('data-root')).toBe('false');
  });

  it('renders node labels', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('node-label-n1').textContent).toBe('Dependency upgrade');
    expect(screen.getByTestId('node-label-n2').textContent).toBe('Breaking API change');
    expect(screen.getByTestId('node-label-n3').textContent).toBe('Build step failed');
  });

  it('renders root badge on the root-cause node', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('root-badge-n2')).toBeDefined();
  });

  it('does NOT render root badge on non-root nodes', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.queryByTestId('root-badge-n1')).toBeNull();
  });

  it('renders edge relation connectors', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('causal-edge-e1')).toBeDefined();
    expect(screen.getByTestId('edge-relation-e1').textContent).toContain('caused');
  });

  it('renders edge explanations', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('edge-explanation-e1').textContent).toContain(
      'The upgrade introduced a breaking change.',
    );
  });

  it('renders the causal-chain-view container', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('causal-chain-view')).toBeDefined();
  });

  it('renders confidence bar for each node', () => {
    const chain = makeCausalChain();
    render(<CausalChainView chain={chain} />);
    expect(screen.getByTestId('confidence-bar-n1')).toBeDefined();
    expect(screen.getByTestId('confidence-bar-n2')).toBeDefined();
  });
});

// ===========================================================================
// EvidenceCard — supporting evidence display
// ===========================================================================

describe('EvidenceCard — supporting evidence display', () => {
  it('renders the evidence summary', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} />);
    expect(screen.getByTestId(`ec-summary-${ev.evidence_id}`).textContent).toBe(ev.summary);
  });

  it('renders the evidence type badge', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} />);
    const badge = screen.getByTestId(`ec-type-badge-${ev.evidence_id}`);
    expect(badge.textContent?.toLowerCase()).toContain('failure');
  });

  it('renders the confidence bar', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} />);
    const bar = screen.getByTestId(`ec-confidence-bar-${ev.evidence_id}`);
    // 95% confidence → width should be 95%
    expect(bar.style.width).toBe('95%');
  });

  it('shows Inspect button when onInspect is provided', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} onInspect={() => undefined} />);
    expect(screen.getByTestId(`ec-inspect-btn-${ev.evidence_id}`)).toBeDefined();
  });

  it('does NOT show Inspect button when onInspect is omitted', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} />);
    expect(screen.queryByTestId(`ec-inspect-btn-${ev.evidence_id}`)).toBeNull();
  });

  it('data-active="false" by default', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} />);
    expect(screen.getByTestId(`evidence-card-${ev.evidence_id}`).getAttribute('data-active')).toBe('false');
  });

  it('data-active="true" when active prop is passed', () => {
    const ev = makeFailureEvidence();
    render(<EvidenceCard evidence={ev as AnyEvidence} active />);
    expect(screen.getByTestId(`evidence-card-${ev.evidence_id}`).getAttribute('data-active')).toBe('true');
  });

  it('calls onInspect when the Inspect button is clicked', () => {
    const ev = makeFailureEvidence();
    let called = false;
    render(
      <EvidenceCard
        evidence={ev as AnyEvidence}
        onInspect={() => { called = true; }}
      />,
    );
    fireEvent.click(screen.getByTestId(`ec-inspect-btn-${ev.evidence_id}`));
    expect(called).toBe(true);
  });
});

// ===========================================================================
// TechnicalDrill — technical detail view
// ===========================================================================

describe('TechnicalDrill — failure evidence', () => {
  it('renders the technical-drill container', () => {
    render(<TechnicalDrill evidence={makeFailureEvidence() as AnyEvidence} />);
    expect(screen.getByTestId('technical-drill')).toBeDefined();
  });

  it('data-evidence-type matches the evidence type', () => {
    const ev = makeFailureEvidence();
    render(<TechnicalDrill evidence={ev as AnyEvidence} />);
    expect(screen.getByTestId('technical-drill').getAttribute('data-evidence-type')).toBe('failure');
  });

  it('renders stack trace section for failure evidence', () => {
    render(<TechnicalDrill evidence={makeFailureEvidence() as AnyEvidence} />);
    // Section is collapsed by default — the toggle button should exist
    expect(screen.getByTestId('td-stack-trace-toggle')).toBeDefined();
  });

  it('opens stack trace section when toggle is clicked', () => {
    render(<TechnicalDrill evidence={makeFailureEvidence() as AnyEvidence} />);
    fireEvent.click(screen.getByTestId('td-stack-trace-toggle'));
    expect(screen.getByTestId('td-stack-trace-code')).toBeDefined();
    expect(screen.getByTestId('td-stack-trace-code').textContent).toContain('at build.js:42');
  });

  it('stack trace section is collapsed (content hidden) by default', () => {
    render(<TechnicalDrill evidence={makeFailureEvidence() as AnyEvidence} />);
    // Content element should not exist until toggled
    expect(screen.queryByTestId('td-stack-trace-content')).toBeNull();
  });
});

describe('TechnicalDrill — test evidence', () => {
  it('renders for test evidence type', () => {
    render(<TechnicalDrill evidence={makeTestEvidence() as AnyEvidence} />);
    expect(screen.getByTestId('technical-drill').getAttribute('data-evidence-type')).toBe('test');
  });

  it('renders failed tests section open by default', () => {
    render(<TechnicalDrill evidence={makeTestEvidence() as AnyEvidence} />);
    // defaultOpen=true for failed tests — content should be immediately present
    expect(screen.getByTestId('td-failed-tests-content')).toBeDefined();
    expect(screen.getByTestId('td-failed-tests-content').textContent).toContain('testFlattenArray');
  });

  it('shows failed test count in the summary row', () => {
    render(<TechnicalDrill evidence={makeTestEvidence() as AnyEvidence} />);
    // Look for the "N failed" text — rendered outside any section
    expect(screen.getByTestId('technical-drill').textContent).toContain('3 failed');
  });
});

describe('TechnicalDrill — historical evidence', () => {
  it('renders known fix when present', () => {
    render(<TechnicalDrill evidence={makeHistoricalEvidence() as AnyEvidence} />);
    expect(screen.getByTestId('td-known-fix').textContent).toContain('Pin lodash');
  });

  it('similar failures section exists when there are similar failures', () => {
    render(<TechnicalDrill evidence={makeHistoricalEvidence() as AnyEvidence} />);
    expect(screen.getByTestId('td-similar-failures-toggle')).toBeDefined();
  });
});

// ===========================================================================
// EvidencePanel integration — TechnicalDrill inline toggle
// ===========================================================================

describe('EvidencePanel integration — TechnicalDrill toggle', () => {
  function setupWithEvidence() {
    const chain = makeCausalChain();
    const failEv = makeFailureEvidence();
    const testEv = makeTestEvidence();
    usePipelineStore.getState().setCausalChain(chain);
    usePipelineStore.getState().setEvidenceForAgent('log_investigator', failEv as AnyEvidence);
    usePipelineStore.getState().setEvidenceForAgent('test_investigator', testEv as AnyEvidence);
  }

  it('shows the evidence accordion when evidence is present', () => {
    setupWithEvidence();
    render(<EvidencePanel />);
    expect(screen.getByTestId('accordion-evidence')).toBeDefined();
  });

  it('evidence accordion starts collapsed (content hidden)', () => {
    setupWithEvidence();
    render(<EvidencePanel />);
    // defaultOpen=false — content not rendered until opened
    expect(screen.queryByTestId('accordion-evidence-content')).toBeNull();
  });

  it('opening evidence accordion reveals evidence cards', () => {
    setupWithEvidence();
    render(<EvidencePanel />);
    fireEvent.click(screen.getByTestId('accordion-evidence-toggle'));
    // Both evidence cards should now be visible
    expect(screen.getByTestId('evidence-card-ev-fail-001')).toBeDefined();
    expect(screen.getByTestId('evidence-card-ev-test-001')).toBeDefined();
  });

  it('clicking Inspect shows TechnicalDrill for that card', () => {
    setupWithEvidence();
    render(<EvidencePanel />);
    // Open the evidence accordion first
    fireEvent.click(screen.getByTestId('accordion-evidence-toggle'));
    // Click Inspect on the failure card
    fireEvent.click(screen.getByTestId('ec-inspect-btn-ev-fail-001'));
    // TechnicalDrill should now be visible
    const drill = screen.getByTestId('technical-drill');
    expect(drill.getAttribute('data-evidence-id')).toBe('ev-fail-001');
  });

  it('clicking Inspect again hides TechnicalDrill (toggle)', () => {
    setupWithEvidence();
    render(<EvidencePanel />);
    fireEvent.click(screen.getByTestId('accordion-evidence-toggle'));
    fireEvent.click(screen.getByTestId('ec-inspect-btn-ev-fail-001'));
    // Now click again to close
    fireEvent.click(screen.getByTestId('ec-inspect-btn-ev-fail-001'));
    expect(screen.queryByTestId('technical-drill')).toBeNull();
  });

  it('only one TechnicalDrill is shown at a time', () => {
    setupWithEvidence();
    render(<EvidencePanel />);
    fireEvent.click(screen.getByTestId('accordion-evidence-toggle'));
    // Open drill for failure
    fireEvent.click(screen.getByTestId('ec-inspect-btn-ev-fail-001'));
    // Open drill for test (should close the failure one)
    fireEvent.click(screen.getByTestId('ec-inspect-btn-ev-test-001'));
    const drills = screen.getAllByTestId('technical-drill');
    expect(drills).toHaveLength(1);
    expect(drills[0].getAttribute('data-evidence-id')).toBe('ev-test-001');
  });
});
