/**
 * initialGraph — MVP topology for the Pipeline Autopilot canvas.
 *
 * 5 service nodes arranged in a pipeline topology:
 *   API Gateway → Auth Service → Payments Service → Database
 *                                                 ↘ Notification Service
 *
 * 6 investigation agent nodes arranged in a row below the services.
 *
 * Edges are meaningful connections between services.
 * Failure edges (failureEdge type) connect affected services.
 * Agent edges use animatedEdge type.
 */

import type { Node, Edge } from '@xyflow/react';

// ---------------------------------------------------------------------------
// Service node positions (spread across a ~1200px wide canvas)
// ---------------------------------------------------------------------------

// Service nodes form a pipeline topology across the top half of the canvas.
// Y positions kept compact so the row is clearly above the agent row.
export const INITIAL_SERVICE_NODES: Node[] = [
  {
    id: 'api-gateway',
    type: 'serviceNode',
    position: { x: 60, y: 60 },
    data: { label: 'API Gateway', icon: '⬡', health: 'HEALTHY' },
  },
  {
    id: 'auth-service',
    type: 'serviceNode',
    position: { x: 310, y: 20 },
    data: { label: 'Auth Service', icon: '🔐', health: 'HEALTHY' },
  },
  {
    id: 'payments-service',
    type: 'serviceNode',
    position: { x: 580, y: 20 },
    data: { label: 'Payments Service', icon: '💳', health: 'HEALTHY' },
  },
  {
    id: 'database',
    type: 'serviceNode',
    position: { x: 850, y: 20 },
    data: { label: 'Database', icon: '🗄', health: 'HEALTHY' },
  },
  {
    id: 'notification-service',
    type: 'serviceNode',
    position: { x: 850, y: 170 },
    data: { label: 'Notification Service', icon: '🔔', health: 'HEALTHY' },
  },
];

// ---------------------------------------------------------------------------
// Agent node positions (row below services)
// Agent nodes sit well below services so they remain visible even when
// CounterfactualSplit occupies the bottom 26% of the viewport.
// The React Flow canvas uses fitView — absolute Y matters only for relative
// placement; fitView will scale the entire graph to fit.
// ---------------------------------------------------------------------------

export const INITIAL_AGENT_NODES: Node[] = [
  {
    id: 'agent-logs',
    type: 'agentNode',
    position: { x: 30, y: 340 },
    data: { label: 'Log Investigator', agentId: 'log_investigator' },
  },
  {
    id: 'agent-code',
    type: 'agentNode',
    position: { x: 195, y: 340 },
    data: { label: 'Code Investigator', agentId: 'code_investigator' },
  },
  {
    id: 'agent-deps',
    type: 'agentNode',
    position: { x: 370, y: 340 },
    data: { label: 'Dependency Investigator', agentId: 'dependency_investigator' },
  },
  {
    id: 'agent-tests',
    type: 'agentNode',
    position: { x: 545, y: 340 },
    data: { label: 'Test Investigator', agentId: 'test_investigator' },
  },
  {
    id: 'agent-infra',
    type: 'agentNode',
    position: { x: 715, y: 340 },
    data: { label: 'Infra Investigator', agentId: 'infra_investigator' },
  },
  {
    id: 'agent-history',
    type: 'agentNode',
    position: { x: 890, y: 340 },
    data: { label: 'History Investigator', agentId: 'history_investigator' },
  },
];

// ---------------------------------------------------------------------------
// Edges — service mesh connections
// ---------------------------------------------------------------------------

export const INITIAL_EDGES: Edge[] = [
  { id: 'e-api-auth',    source: 'api-gateway',       target: 'auth-service',         type: 'animatedEdge' },
  { id: 'e-auth-pay',   source: 'auth-service',        target: 'payments-service',     type: 'animatedEdge' },
  { id: 'e-pay-db',     source: 'payments-service',    target: 'database',             type: 'failureEdge'  },
  { id: 'e-pay-notify', source: 'payments-service',    target: 'notification-service', type: 'animatedEdge' },
  { id: 'e-api-pay',    source: 'api-gateway',         target: 'payments-service',     type: 'animatedEdge' },
];

// ---------------------------------------------------------------------------
// Combined initial topology
// ---------------------------------------------------------------------------

export const INITIAL_GRAPH_NODES: Node[] = [
  ...INITIAL_SERVICE_NODES,
  ...INITIAL_AGENT_NODES,
];

export const INITIAL_GRAPH_EDGES: Edge[] = INITIAL_EDGES;
