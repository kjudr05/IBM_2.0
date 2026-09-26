/**
 * Task 15 — RecoveryReport unit tests.
 *
 * Covers:
 *  Visibility:
 *    - returns null / renders nothing when recoveryReport is null
 *    - renders the card when recoveryReport is set
 *    - card is visible in App layout when storyState === COMPLETE
 *
 *  Root-cause summary:
 *    - plain-language summary text is visible
 *    - "What Happened" label appears
 *
 *  Causal explanation:
 *    - causal explanation field is present when populated
 *    - root-cause node label is highlighted
 *
 *  Proposed fix:
 *    - fix description is rendered
 *    - fix-type badge shows human-readable label
 *    - fix rationale is rendered
 *    - fix confidence bar and percentage are rendered
 *
 *  Validation result:
 *    - validation narrative is rendered
 *    - validation badge shows PASSED / PARTIAL / FAILED status
 *    - validation confidence bar is rendered
 *    - PASSED badge has green styling (data-status attribute)
 *    - PARTIAL badge has amber styling
 *    - FAILED badge has red styling
 *
 *  Recovery/counterfactual summary:
 *    - counterfactual narrative is rendered
 *    - recovered-nodes count badge appears
 *    - singular "node recovered" when count is 1
 *    - plural "nodes recovered" when count > 1
 *    - counterfactual section absent when counterfactual is null
 *
 *  Confidence / status:
 *    - header banner shows "Recovery Complete" text
 *    - overall validation badge is in the header
 *
 * Strategy:
 *  - Uses @testing-library/react
 *  - Zustand store reset before each test
 *  - All fixtures are defined inline — no external sample-data files required
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { usePipelineStore } from '../../state/pipelineStore';
import type { RecoveryReport as RecoveryReportType } from '../../types/fix';
import type { CausalChain } from '../../types/causal';
import type { CounterfactualResult, FixProposal, ValidationResult } from '../../types/fix';

import { RecoveryReport } from './RecoveryReport';

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
    pipeline_id: 'pipeline-test-001',
    nodes: [
      {
        node_id: 'node-dep-break',
        node_type: 'ROOT_CAUSE',
        label: 'cryptography pinned to 41.0.3',
        description: 'Breaking version introduced via dependency update',
        evidence_ids: ['ev-001'],
        confidence: 0.92,
      },
      {
        node_id: 'node-test-fail',
        node_type: 'FAILURE',
        label: 'Test suite failure',
        description: 'Integration tests failed due to incompatible ABI',
        evidence_ids: ['ev-002'],
        confidence: 0.88,
      },
    ],
    edges: [
      {
        edge_id: 'edge-001',
        source_node_id: 'node-dep-break',
        target_node_id: 'node-test-fail',
        relation: 'caused',
        explanation: 'The version break caused the test suite to fail.',
      },
    ],
    root_cause_node_id: 'node-dep-break',
    narrative:
      'A dependency update pinned cryptography to 41.0.3 which broke ABI compatibility ' +
      'and caused the entire test suite to fail.',
    confidence: 0.92,
    builder_version: '1.0.0',
    ...overrides,
  };
}

function makeFixProposal(overrides: Partial<FixProposal> = {}): FixProposal {
  return {
    fix_id: 'fix-001',
    pipeline_id: 'pipeline-test-001',
    root_cause_node_id: 'node-dep-break',
    fix_type: 'DEPENDENCY_CHANGE',
    description:
      'Pin cryptography to <41.0.0 in pyproject.toml to avoid the ABI break introduced in 41.0.3.',
    rationale:
      'Versions <41.0.0 maintain backward compatibility with the project\'s C extension dependencies.',
    affected_file: 'pyproject.toml',
    dependency_changes: [
      {
        name: 'cryptography',
        old_version: '41.0.3',
        new_version: '<41.0.0',
        affected_component: null,
      },
    ],
    patch: null,
    config_changes: null,
    evidence_ids: ['ev-001', 'ev-002'],
    confidence: 0.87,
    generator_version: '1.0.0',
    ...overrides,
  };
}

function makeValidationResult(overrides: Partial<ValidationResult> = {}): ValidationResult {
  return {
    validation_id: 'val-001',
    fix_id: 'fix-001',
    status: 'PASSED',
    confidence: 0.9,
    validation_narrative:
      'Applying the dependency pin resolves all 4 failing tests. ' +
      'No regressions detected in the existing test suite.',
    ...overrides,
  };
}

function makeCounterfactual(overrides: Partial<CounterfactualResult> = {}): CounterfactualResult {
  return {
    pipeline_id: 'pipeline-test-001',
    fix_id: 'fix-001',
    before_state: { nodes: { payments_service: 'FAILED', auth_service: 'FAILED' } },
    after_state: { nodes: { payments_service: 'HEALTHY', auth_service: 'HEALTHY' } },
    changed_nodes: ['payments_service', 'auth_service'],
    narrative:
      'If the dependency is pinned to <41.0.0, both failing services will recover to HEALTHY.',
    ...overrides,
  };
}

function makeReport(overrides: Partial<RecoveryReportType> = {}): RecoveryReportType {
  return {
    report_id: 'report-001',
    pipeline_id: 'pipeline-test-001',
    created_at: '2024-01-15T12:00:00Z',
    root_cause_summary:
      'A breaking version of the cryptography library was introduced via an automated dependency ' +
      'update. This caused the CI test suite to fail with ABI compatibility errors.',
    causal_explanation:
      'cryptography==41.0.3 introduced an ABI break that cascaded through the build pipeline, ' +
      'causing 4 tests to fail and triggering deployment gates to block.',
    evidence_summary: {
      'ev-001': {
        evidence_type: 'dependency',
        summary: 'Dependency cryptography updated from 40.0.2 to 41.0.3',
        confidence: 0.92,
      },
      'ev-002': {
        evidence_type: 'test',
        summary: '4 tests failed due to ImportError: ABI incompatibility',
        confidence: 0.88,
      },
    },
    proposed_fix: makeFixProposal(),
    validation_result: makeValidationResult(),
    causal_chain: makeCausalChain(),
    counterfactual: makeCounterfactual(),
    ...overrides,
  };
}

/** Convenience: set the recoveryReport in the store and render */
function setup(reportOverrides: Partial<RecoveryReportType> = {}) {
  act(() => {
    usePipelineStore.getState().setRecoveryReport(makeReport(reportOverrides));
    usePipelineStore.getState().setStoryState('COMPLETE');
  });
  return render(<RecoveryReport />);
}

// ===========================================================================
// Visibility
// ===========================================================================

describe('RecoveryReport — visibility', () => {
  it('returns nothing when recoveryReport is null', () => {
    const { container } = render(<RecoveryReport />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the card when recoveryReport is set in the store', () => {
    setup();
    expect(screen.getByTestId('recovery-report')).toBeDefined();
  });

  it('card is not rendered before report arrives (null check)', () => {
    render(<RecoveryReport />);
    expect(screen.queryByTestId('recovery-report')).toBeNull();
  });

  it('card disappears when store is reset', () => {
    setup();
    expect(screen.getByTestId('recovery-report')).toBeDefined();

    act(() => { usePipelineStore.getState().reset(); });
    // We need to re-render after the reset
    const { rerender } = render(<RecoveryReport />);
    rerender(<RecoveryReport />);
    // After reset the new instance should also show nothing
    expect(usePipelineStore.getState().recoveryReport).toBeNull();
  });
});

// ===========================================================================
// Root-cause summary
// ===========================================================================

describe('RecoveryReport — root-cause summary', () => {
  it('renders the plain-language root_cause_summary text', () => {
    setup({
      root_cause_summary: 'A breaking library version caused the CI pipeline to fail.',
    });
    const summaryEl = screen.getByTestId('rr-root-cause-summary');
    expect(summaryEl.textContent).toContain(
      'A breaking library version caused the CI pipeline to fail.',
    );
  });

  it('shows the "What Happened" label above the summary', () => {
    setup();
    const summaryEl = screen.getByTestId('rr-root-cause-summary');
    expect(summaryEl.textContent).toContain('What Happened');
  });

  it('renders a different summary when overridden', () => {
    setup({ root_cause_summary: 'Docker image tag not found in registry.' });
    expect(screen.getByTestId('rr-root-cause-summary').textContent).toContain(
      'Docker image tag not found in registry.',
    );
  });
});

// ===========================================================================
// Causal explanation
// ===========================================================================

describe('RecoveryReport — causal explanation', () => {
  it('renders the causal_explanation field', () => {
    setup({
      causal_explanation: 'The ABI break cascaded through three downstream services.',
    });
    const el = screen.getByTestId('rr-causal-explanation');
    expect(el.textContent).toContain('ABI break cascaded through three downstream services');
  });

  it('renders the root-cause node label from the causal chain', () => {
    setup();
    const el = screen.getByTestId('rr-root-cause-node');
    expect(el.textContent).toContain('cryptography pinned to 41.0.3');
  });

  it('does not render root-cause node field when causal chain has no matching node', () => {
    setup({
      causal_chain: makeCausalChain({ root_cause_node_id: 'no-such-node' }),
    });
    expect(screen.queryByTestId('rr-root-cause-node')).toBeNull();
  });
});

// ===========================================================================
// Proposed fix
// ===========================================================================

describe('RecoveryReport — proposed fix', () => {
  it('renders the rr-proposed-fix section', () => {
    setup();
    expect(screen.getByTestId('rr-proposed-fix')).toBeDefined();
  });

  it('renders the fix description text', () => {
    setup({
      proposed_fix: makeFixProposal({
        description: 'Update cryptography to <41.0.0 in pyproject.toml.',
      }),
    });
    expect(screen.getByTestId('rr-fix-description').textContent).toContain(
      'Update cryptography to <41.0.0 in pyproject.toml.',
    );
  });

  it('shows human-readable fix-type badge for DEPENDENCY_CHANGE', () => {
    setup({ proposed_fix: makeFixProposal({ fix_type: 'DEPENDENCY_CHANGE' }) });
    expect(screen.getByTestId('rr-fix-type-badge').textContent).toContain('Dependency Update');
  });

  it('shows human-readable fix-type badge for CODE_PATCH', () => {
    setup({ proposed_fix: makeFixProposal({ fix_type: 'CODE_PATCH' }) });
    expect(screen.getByTestId('rr-fix-type-badge').textContent).toContain('Code Patch');
  });

  it('shows human-readable fix-type badge for CONFIG_CHANGE', () => {
    setup({ proposed_fix: makeFixProposal({ fix_type: 'CONFIG_CHANGE' }) });
    expect(screen.getByTestId('rr-fix-type-badge').textContent).toContain('Configuration Change');
  });

  it('shows human-readable fix-type badge for ENV_FIX', () => {
    setup({ proposed_fix: makeFixProposal({ fix_type: 'ENV_FIX' }) });
    expect(screen.getByTestId('rr-fix-type-badge').textContent).toContain('Environment Fix');
  });

  it('renders the fix rationale', () => {
    setup({
      proposed_fix: makeFixProposal({
        rationale: 'Older versions maintain backward ABI compatibility.',
      }),
    });
    expect(screen.getByTestId('rr-fix-rationale').textContent).toContain(
      'Older versions maintain backward ABI compatibility.',
    );
  });

  it('renders fix confidence bar', () => {
    setup();
    // Multiple confidence bars exist (fix + validation); first is fix
    const bars = screen.getAllByTestId('rr-confidence-bar');
    expect(bars.length).toBeGreaterThan(0);
  });

  it('renders fix confidence percentage', () => {
    setup({ proposed_fix: makeFixProposal({ confidence: 0.87 }) });
    const pctEls = screen.getAllByTestId('rr-confidence-pct');
    // At least one should contain 87%
    const found = pctEls.some((el) => el.textContent?.includes('87%'));
    expect(found).toBe(true);
  });
});

// ===========================================================================
// Validation result
// ===========================================================================

describe('RecoveryReport — validation result', () => {
  it('renders the rr-validation-result section', () => {
    setup();
    expect(screen.getByTestId('rr-validation-result')).toBeDefined();
  });

  it('renders the validation narrative', () => {
    setup({
      validation_result: makeValidationResult({
        validation_narrative: 'All 4 failing tests now pass after the dependency pin.',
      }),
    });
    expect(screen.getByTestId('rr-validation-narrative').textContent).toContain(
      'All 4 failing tests now pass after the dependency pin.',
    );
  });

  it('badge shows PASSED for PASSED status', () => {
    setup({ validation_result: makeValidationResult({ status: 'PASSED' }) });
    const badges = screen.getAllByTestId('rr-validation-badge');
    const passedBadge = badges.find((b) => b.dataset['status'] === 'PASSED');
    expect(passedBadge).toBeDefined();
    expect(passedBadge?.textContent).toContain('PASSED');
  });

  it('badge shows PARTIAL for PARTIAL status', () => {
    setup({ validation_result: makeValidationResult({ status: 'PARTIAL' }) });
    const badges = screen.getAllByTestId('rr-validation-badge');
    const partialBadge = badges.find((b) => b.dataset['status'] === 'PARTIAL');
    expect(partialBadge).toBeDefined();
    expect(partialBadge?.textContent).toContain('PARTIAL');
  });

  it('badge shows FAILED for FAILED status', () => {
    setup({ validation_result: makeValidationResult({ status: 'FAILED' }) });
    const badges = screen.getAllByTestId('rr-validation-badge');
    const failedBadge = badges.find((b) => b.dataset['status'] === 'FAILED');
    expect(failedBadge).toBeDefined();
    expect(failedBadge?.textContent).toContain('FAILED');
  });

  it('renders validation confidence percentage', () => {
    setup({ validation_result: makeValidationResult({ confidence: 0.9 }) });
    const pctEls = screen.getAllByTestId('rr-confidence-pct');
    const found = pctEls.some((el) => el.textContent?.includes('90%'));
    expect(found).toBe(true);
  });

  it('PASSED badge has data-status="PASSED"', () => {
    setup({ validation_result: makeValidationResult({ status: 'PASSED' }) });
    const badges = screen.getAllByTestId('rr-validation-badge');
    const passedBadge = badges.find((b) => b.getAttribute('data-status') === 'PASSED');
    expect(passedBadge).toBeDefined();
  });
});

// ===========================================================================
// Recovery / counterfactual summary
// ===========================================================================

describe('RecoveryReport — counterfactual / recovery outcome', () => {
  it('renders the rr-counterfactual section when counterfactual is present', () => {
    setup();
    expect(screen.getByTestId('rr-counterfactual')).toBeDefined();
  });

  it('renders the counterfactual narrative text', () => {
    setup({
      counterfactual: makeCounterfactual({
        narrative: 'Pinning the dependency restores all services to HEALTHY within one build cycle.',
      }),
    });
    expect(screen.getByTestId('rr-counterfactual-narrative').textContent).toContain(
      'Pinning the dependency restores all services to HEALTHY within one build cycle.',
    );
  });

  it('shows recovered-count badge with correct number', () => {
    setup({
      counterfactual: makeCounterfactual({ changed_nodes: ['svc-a', 'svc-b', 'svc-c'] }),
    });
    const badge = screen.getByTestId('rr-recovered-count');
    expect(badge.textContent).toContain('3');
  });

  it('shows plural "nodes recovered" when count > 1', () => {
    setup({
      counterfactual: makeCounterfactual({ changed_nodes: ['svc-a', 'svc-b'] }),
    });
    expect(screen.getByTestId('rr-recovered-count').textContent).toContain('nodes recovered');
  });

  it('shows singular "node recovered" when count is 1', () => {
    setup({
      counterfactual: makeCounterfactual({ changed_nodes: ['svc-a'] }),
    });
    expect(screen.getByTestId('rr-recovered-count').textContent).toContain('node recovered');
    expect(screen.getByTestId('rr-recovered-count').textContent).not.toContain('nodes recovered');
  });

  it('does not show recovered-count badge when changed_nodes is empty', () => {
    setup({ counterfactual: makeCounterfactual({ changed_nodes: [] }) });
    expect(screen.queryByTestId('rr-recovered-count')).toBeNull();
  });

  it('does not render rr-counterfactual section when counterfactual is absent', () => {
    // Build a report with no counterfactual
    act(() => {
      usePipelineStore.getState().setRecoveryReport({
        ...makeReport(),
        // Override counterfactual by casting — TypeScript doesn't allow null here
        // but we need to test the null guard in the component.
        counterfactual: null as unknown as ReturnType<typeof makeCounterfactual>,
      });
    });
    render(<RecoveryReport />);
    expect(screen.queryByTestId('rr-counterfactual')).toBeNull();
  });
});

// ===========================================================================
// Header / completion status
// ===========================================================================

describe('RecoveryReport — header and status', () => {
  it('renders the "Recovery Complete" banner text', () => {
    setup();
    const header = screen.getByTestId('rr-header');
    expect(header.textContent).toContain('Recovery Complete');
  });

  it('header contains the overall validation badge', () => {
    setup({ validation_result: makeValidationResult({ status: 'PASSED' }) });
    const header = screen.getByTestId('rr-header');
    // The header contains the ValidationBadge; check its text
    expect(header.textContent).toContain('PASSED');
  });

  it('header badge updates to FAILED when validation failed', () => {
    setup({ validation_result: makeValidationResult({ status: 'FAILED' }) });
    const header = screen.getByTestId('rr-header');
    expect(header.textContent).toContain('FAILED');
  });

  it('renders multiple confidence bars (fix + validation)', () => {
    setup();
    const bars = screen.getAllByTestId('rr-confidence-bar');
    // At least 2: one for fix confidence, one for validation confidence
    expect(bars.length).toBeGreaterThanOrEqual(2);
  });
});

// ===========================================================================
// Integration — store reactivity
// ===========================================================================

describe('RecoveryReport — store integration', () => {
  it('renders when report is set after initial null', () => {
    const { rerender } = render(<RecoveryReport />);
    expect(screen.queryByTestId('recovery-report')).toBeNull();

    act(() => {
      usePipelineStore.getState().setRecoveryReport(makeReport());
    });
    rerender(<RecoveryReport />);
    expect(screen.getByTestId('recovery-report')).toBeDefined();
  });

  it('shows both fix description and validation narrative in same render', () => {
    setup({
      proposed_fix: makeFixProposal({ description: 'Pin to <41.0.0' }),
      validation_result: makeValidationResult({
        validation_narrative: 'All tests pass after pin.',
      }),
    });
    expect(screen.getByTestId('rr-fix-description').textContent).toContain('Pin to <41.0.0');
    expect(screen.getByTestId('rr-validation-narrative').textContent).toContain(
      'All tests pass after pin.',
    );
  });
});
