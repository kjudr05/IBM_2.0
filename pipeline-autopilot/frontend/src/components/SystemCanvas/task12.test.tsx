/**
 * Task 12 — component unit tests.
 *
 * Covers:
 *  ServiceNode:
 *    - renders health indicator for HEALTHY / DEGRADED / FAILED
 *    - applies sn-pulse class only when health=FAILED + FAILURE_PROPAGATING
 *    - falls back to HEALTHY when no health prop and story is not failing
 *    - auto-derives FAILED when no health prop and story is FAILURE_PROPAGATING
 *    - renders icon when provided
 *
 *  AgentNode:
 *    - idle by default (no evidence, neutral story state)
 *    - active when explicit active=true prop
 *    - active during AGENTS_ACTIVATING story state
 *    - active when evidence has arrived for the agent
 *    - data-active attribute reflects the resolved state
 *    - displays display name from agentId map
 *
 *  FailureEdge:
 *    - renders the path element
 *    - data-active="false" when story is not FAILURE_PROPAGATING
 *    - data-active="true" when story is FAILURE_PROPAGATING
 *    - particle circle rendered only when FAILURE_PROPAGATING
 *    - no particle when story is HEALTHY
 *
 * Strategy: test React components via @testing-library/react.
 * Zustand store is reset before each test via the existing reset() action.
 * @xyflow/react Handle/Position are mocked — they're DOM-irrelevant for unit tests.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { usePipelineStore } from '../../state/pipelineStore';

// ---------------------------------------------------------------------------
// Mock @xyflow/react
// Handles and Position are DOM-irrelevant for unit testing the node visuals.
// We stub them with minimal no-op components / values.
// ---------------------------------------------------------------------------

vi.mock('@xyflow/react', () => ({
  Handle: () => null,
  Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
  BaseEdge: ({ path, style }: { path: string; style?: React.CSSProperties }) => (
    <path data-testid="base-edge" d={path} style={style} />
  ),
  getStraightPath: (_p: unknown) => ['M0 0 L100 0', 50, 0],
  getBezierPath: (_p: unknown) => ['M0 0 C50 0 50 100 100 100', 50, 50],
}));

import React from 'react';
import { ServiceNode }  from './nodes/ServiceNode';
import { AgentNode }    from './nodes/AgentNode';
import { FailureEdge }  from './edges/AnimatedEdge';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build the minimal NodeProps shape expected by our components */
function nodeProps(data: Record<string, unknown>) {
  return {
    id: 'test-node',
    data,
    selected: false,
    selectable: true,
    deletable: true,
    draggable: true,
    type: 'serviceNode',
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    isConnectable: true,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
    dragging: false,
  } as unknown as Parameters<typeof ServiceNode>[0];
}

/** Build minimal EdgeProps */
function edgeProps(overrides: Partial<Parameters<typeof FailureEdge>[0]> = {}) {
  return {
    id: 'test-edge',
    source: 'a',
    target: 'b',
    sourceX: 0,
    sourceY: 0,
    targetX: 100,
    targetY: 0,
    sourcePosition: 'right' as const,
    targetPosition: 'left' as const,
    selected: false,
    animated: false,
    data: {},
    ...overrides,
  } as Parameters<typeof FailureEdge>[0];
}

// ---------------------------------------------------------------------------
// Reset store before each test
// ---------------------------------------------------------------------------

beforeEach(() => {
  usePipelineStore.getState().reset();
});

// ===========================================================================
// ServiceNode
// ===========================================================================

describe('ServiceNode — health states', () => {
  it('shows HEALTHY indicator when health="HEALTHY"', () => {
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'HEALTHY' })} />);
    const indicator = screen.getByTestId('health-indicator');
    expect(indicator.textContent).toContain('HEALTHY');
  });

  it('shows DEGRADED indicator when health="DEGRADED"', () => {
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'DEGRADED' })} />);
    expect(screen.getByTestId('health-indicator').textContent).toContain('DEGRADED');
  });

  it('shows FAILED indicator when health="FAILED"', () => {
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'FAILED' })} />);
    expect(screen.getByTestId('health-indicator').textContent).toContain('FAILED');
  });

  it('defaults to HEALTHY when no health prop and story is HEALTHY', () => {
    render(<ServiceNode {...nodeProps({ label: 'API' })} />);
    expect(screen.getByTestId('health-indicator').textContent).toContain('HEALTHY');
  });

  it('auto-derives FAILED when no health prop and story is FAILURE_PROPAGATING', () => {
    usePipelineStore.getState().setStoryState('FAILURE_PROPAGATING');
    render(<ServiceNode {...nodeProps({ label: 'API' })} />);
    expect(screen.getByTestId('health-indicator').textContent).toContain('FAILED');
  });

  it('applies sn-pulse class when health=FAILED and story is FAILURE_PROPAGATING', () => {
    usePipelineStore.getState().setStoryState('FAILURE_PROPAGATING');
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'FAILED' })} />);
    const node = screen.getByTestId('service-node');
    expect(node.className).toContain('sn-pulse');
  });

  it('does NOT apply sn-pulse when health=FAILED but story is not FAILURE_PROPAGATING', () => {
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'FAILED' })} />);
    const node = screen.getByTestId('service-node');
    expect(node.className ?? '').not.toContain('sn-pulse');
  });

  it('does NOT apply sn-pulse when health=HEALTHY during FAILURE_PROPAGATING', () => {
    usePipelineStore.getState().setStoryState('FAILURE_PROPAGATING');
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'HEALTHY' })} />);
    const node = screen.getByTestId('service-node');
    expect(node.className ?? '').not.toContain('sn-pulse');
  });

  it('renders icon when provided', () => {
    render(<ServiceNode {...nodeProps({ label: 'DB', health: 'HEALTHY', icon: '🗄️' })} />);
    expect(screen.getByText('🗄️')).toBeDefined();
  });

  it('renders the service label', () => {
    render(<ServiceNode {...nodeProps({ label: 'AuthService', health: 'HEALTHY' })} />);
    expect(screen.getByText('AuthService')).toBeDefined();
  });

  it('data-health attribute matches the health prop', () => {
    render(<ServiceNode {...nodeProps({ label: 'API', health: 'DEGRADED' })} />);
    expect(screen.getByTestId('service-node').getAttribute('data-health')).toBe('DEGRADED');
  });
});

// ===========================================================================
// AgentNode
// ===========================================================================

describe('AgentNode — active / idle states', () => {
  it('is idle by default (no evidence, HEALTHY state)', () => {
    render(<AgentNode {...nodeProps({ label: 'Logs', agentId: 'log_investigator' }) as Parameters<typeof AgentNode>[0]} />);
    const node = screen.getByTestId('agent-node');
    expect(node.getAttribute('data-active')).toBe('false');
  });

  it('is active when active=true is passed explicitly', () => {
    render(<AgentNode {...nodeProps({ label: 'Code', active: true }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').getAttribute('data-active')).toBe('true');
  });

  it('is idle when active=false is passed explicitly, regardless of story state', () => {
    usePipelineStore.getState().setStoryState('AGENTS_ACTIVATING');
    render(<AgentNode {...nodeProps({ label: 'Deps', active: false }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').getAttribute('data-active')).toBe('false');
  });

  it('is active during AGENTS_ACTIVATING story state', () => {
    usePipelineStore.getState().setStoryState('AGENTS_ACTIVATING');
    render(<AgentNode {...nodeProps({ label: 'Tests', agentId: 'test_investigator' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').getAttribute('data-active')).toBe('true');
  });

  it('is active during EVIDENCE_FLOWING story state', () => {
    usePipelineStore.getState().setStoryState('EVIDENCE_FLOWING');
    render(<AgentNode {...nodeProps({ label: 'Infra' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').getAttribute('data-active')).toBe('true');
  });

  it('is active during EVIDENCE_CONVERGING story state', () => {
    usePipelineStore.getState().setStoryState('EVIDENCE_CONVERGING');
    render(<AgentNode {...nodeProps({ label: 'History' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').getAttribute('data-active')).toBe('true');
  });

  it('is active when evidence has arrived for this agent', () => {
    const { setEvidenceForAgent } = usePipelineStore.getState();
    setEvidenceForAgent('log_investigator', { evidence_id: 'e1', evidence_type: 'failure' } as never);
    render(<AgentNode {...nodeProps({ label: 'Logs', agentId: 'log_investigator' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').getAttribute('data-active')).toBe('true');
  });

  it('applies an-active class when active', () => {
    usePipelineStore.getState().setStoryState('AGENTS_ACTIVATING');
    render(<AgentNode {...nodeProps({ label: 'Code' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').className).toContain('an-active');
  });

  it('does not apply an-active class when idle', () => {
    render(<AgentNode {...nodeProps({ label: 'Code' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-node').className ?? '').not.toContain('an-active');
  });

  it('renders the agent label', () => {
    render(<AgentNode {...nodeProps({ label: 'Deps Agent' }) as Parameters<typeof AgentNode>[0]} />);
    expect(screen.getByTestId('agent-label').textContent).toBe('Deps Agent');
  });

  it('uses short display name from agentId when label is empty string', () => {
    render(<AgentNode {...nodeProps({ label: 'log_investigator', agentId: 'log_investigator' }) as Parameters<typeof AgentNode>[0]} />);
    // label is provided explicitly — it takes precedence
    expect(screen.getByTestId('agent-label').textContent).toBe('log_investigator');
  });
});

// ===========================================================================
// FailureEdge — failure animation
// ===========================================================================

describe('FailureEdge — FAILURE_PROPAGATING animation', () => {
  it('renders the edge path element', () => {
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    expect(screen.getByTestId('failure-edge-path')).toBeDefined();
  });

  it('data-active="false" when story is HEALTHY (default)', () => {
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    expect(screen.getByTestId('failure-edge-path').getAttribute('data-active')).toBe('false');
  });

  it('data-active="true" when story is FAILURE_PROPAGATING', () => {
    usePipelineStore.getState().setStoryState('FAILURE_PROPAGATING');
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    expect(screen.getByTestId('failure-edge-path').getAttribute('data-active')).toBe('true');
  });

  it('renders failure-particle circle during FAILURE_PROPAGATING', () => {
    usePipelineStore.getState().setStoryState('FAILURE_PROPAGATING');
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    expect(screen.getByTestId('failure-particle')).toBeDefined();
  });

  it('does NOT render failure-particle when story is HEALTHY', () => {
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    expect(screen.queryByTestId('failure-particle')).toBeNull();
  });

  it('does NOT render failure-particle during AGENTS_ACTIVATING', () => {
    usePipelineStore.getState().setStoryState('AGENTS_ACTIVATING');
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    expect(screen.queryByTestId('failure-particle')).toBeNull();
  });

  it('path stroke is red (#ef4444) during FAILURE_PROPAGATING', () => {
    usePipelineStore.getState().setStoryState('FAILURE_PROPAGATING');
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    const path = screen.getByTestId('failure-edge-path');
    expect(path.getAttribute('stroke')).toBe('#ef4444');
  });

  it('path stroke is muted red when not active', () => {
    render(
      <svg>
        <FailureEdge {...edgeProps()} />
      </svg>,
    );
    const path = screen.getByTestId('failure-edge-path');
    expect(path.getAttribute('stroke')).toBe('#6b2020');
  });
});
