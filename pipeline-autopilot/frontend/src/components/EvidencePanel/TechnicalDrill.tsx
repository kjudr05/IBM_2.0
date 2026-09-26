/**
 * TechnicalDrill — Level 3 technical detail view.
 *
 * Task 13: full progressive disclosure with expandable technical sections.
 *
 * Renders type-specific technical detail for a selected evidence artifact:
 *   failure    → stack trace, log excerpt, error class/message
 *   change     → diff hunks, changed files, commit info
 *   dependency → breaking changes, added/removed/changed deps
 *   test       → failed tests, flaky tests, regression tests
 *   infra      → dockerfile issues, CI config issues, env vars
 *   historical → similar failures, recurrence, known fix
 *
 * This component has NO store dependency — it receives the evidence via prop.
 * It is always secondary to the plain-language explanation above it.
 */

import { useState } from 'react';
import type {
  AnyEvidence,
  FailureEvidence,
  ChangeEvidence,
  DependencyEvidence,
  TestRunEvidence,
  InfraEvidence,
  HistoricalEvidence,
} from '../../types/evidence';

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------

interface SectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  testId?: string;
}

function Section({ title, defaultOpen = false, children, testId }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      data-testid={testId}
      style={{ borderTop: '1px solid #1e2030', marginTop: 6 }}
    >
      <button
        data-testid={testId ? `${testId}-toggle` : undefined}
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 0',
          color: '#8b949e',
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}
      >
        <span>{title}</span>
        <span style={{ color: '#57606a', fontSize: 10 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div
          data-testid={testId ? `${testId}-content` : undefined}
          style={{ paddingBottom: 8 }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

function CodeBlock({ text, testId }: { text: string; testId?: string }) {
  return (
    <pre
      data-testid={testId}
      style={{
        fontFamily: '"SF Mono", "Fira Code", monospace',
        fontSize: 10,
        color: '#c9d1d9',
        background: '#0d0d14',
        border: '1px solid #1e2030',
        borderRadius: 5,
        padding: '7px 9px',
        overflowX: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
        margin: '4px 0',
        lineHeight: 1.5,
      }}
    >
      {text}
    </pre>
  );
}

function BulletList({ items, colour = '#8b949e' }: { items: string[]; colour?: string }) {
  if (items.length === 0) return null;
  return (
    <ul style={{ margin: 0, paddingLeft: 14, listStyle: 'disc' }}>
      {items.map((item, i) => (
        <li key={i} style={{ fontSize: 11, color: colour, lineHeight: 1.6, marginBottom: 1 }}>
          {item}
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------------------
// Type-specific drill sections
// ---------------------------------------------------------------------------

function FailureDrill({ ev }: { ev: FailureEvidence }) {
  return (
    <>
      <div style={{ marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: '#ef4444', fontWeight: 600 }}>{ev.error_class}</span>
        <span style={{ fontSize: 10, color: '#8b949e' }}> — {ev.affected_stage}</span>
      </div>
      <div style={{ fontSize: 11, color: '#fca5a5', marginBottom: 6, lineHeight: 1.5 }}>
        {ev.error_message}
      </div>

      {ev.stack_trace.length > 0 && (
        <Section title="Stack Trace" testId="td-stack-trace">
          <CodeBlock text={ev.stack_trace.join('\n')} testId="td-stack-trace-code" />
        </Section>
      )}

      {ev.log_excerpt && (
        <Section title="Log Excerpt" testId="td-log-excerpt">
          <CodeBlock text={ev.log_excerpt} testId="td-log-excerpt-code" />
        </Section>
      )}
    </>
  );
}

function ChangeDrill({ ev }: { ev: ChangeEvidence }) {
  return (
    <>
      <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 6 }}>
        <span style={{ color: '#3b82f6' }}>{ev.commit_sha.slice(0, 8)}</span>
        {ev.author && <span> by {ev.author}</span>}
        {ev.commit_message && (
          <div style={{ marginTop: 3, color: '#c9d1d9', fontStyle: 'italic' }}>
            "{ev.commit_message}"
          </div>
        )}
      </div>

      <div style={{ fontSize: 10, color: '#57606a', marginBottom: 6 }}>
        +{ev.total_additions} / -{ev.total_deletions} lines across {ev.changed_files.length} file{ev.changed_files.length !== 1 ? 's' : ''}
      </div>

      {ev.changed_files.length > 0 && (
        <Section title="Changed Files" testId="td-changed-files">
          {ev.changed_files.map((f, i) => (
            <div key={i} style={{ marginBottom: 4 }}>
              <div style={{ fontSize: 11, color: '#c9d1d9', fontFamily: 'monospace' }}>{f.path}</div>
              <div style={{ fontSize: 10, color: '#57606a' }}>
                +{f.additions} / -{f.deletions}
              </div>
              {f.diff_hunk && (
                <CodeBlock text={f.diff_hunk} testId={`td-diff-hunk-${i}`} />
              )}
            </div>
          ))}
        </Section>
      )}
    </>
  );
}

function DependencyDrill({ ev }: { ev: DependencyEvidence }) {
  return (
    <>
      {ev.breaking_changes.length > 0 && (
        <Section title="Breaking Changes" defaultOpen testId="td-breaking-changes">
          <BulletList items={ev.breaking_changes} colour="#ef4444" />
        </Section>
      )}
      {ev.changed.length > 0 && (
        <Section title="Changed Dependencies" testId="td-changed-deps">
          {ev.changed.map((d, i) => (
            <div key={i} style={{ fontSize: 11, color: '#8b949e', marginBottom: 3, fontFamily: 'monospace' }}>
              {d.name}: <span style={{ color: '#ef4444' }}>{d.old_version ?? '?'}</span>
              {' → '}
              <span style={{ color: '#22c55e' }}>{d.new_version ?? '?'}</span>
            </div>
          ))}
        </Section>
      )}
      {ev.added.length > 0 && (
        <Section title="Added" testId="td-added-deps">
          <BulletList items={ev.added.map((d) => `${d.name}@${d.new_version ?? '?'}`)} colour="#22c55e" />
        </Section>
      )}
      {ev.removed.length > 0 && (
        <Section title="Removed" testId="td-removed-deps">
          <BulletList items={ev.removed.map((d) => `${d.name}@${d.old_version ?? '?'}`)} colour="#ef4444" />
        </Section>
      )}
    </>
  );
}

function TestDrill({ ev }: { ev: TestRunEvidence }) {
  return (
    <>
      <div style={{ fontSize: 10, color: '#57606a', marginBottom: 6 }}>
        {ev.total_passed}/{ev.total_run} passed
        {ev.total_failed > 0 && (
          <span style={{ color: '#ef4444' }}> · {ev.total_failed} failed</span>
        )}
        {ev.total_skipped > 0 && (
          <span style={{ color: '#eab308' }}> · {ev.total_skipped} skipped</span>
        )}
      </div>

      {ev.failed_tests.length > 0 && (
        <Section title="Failed Tests" defaultOpen testId="td-failed-tests">
          {ev.failed_tests.map((t, i) => (
            <div key={i} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 11, color: '#ef4444', fontFamily: 'monospace' }}>
                {t.class_name ? `${t.class_name}::` : ''}{t.name}
              </div>
              <div style={{ fontSize: 10, color: '#8b949e', lineHeight: 1.5 }}>
                {t.failure_message}
              </div>
            </div>
          ))}
        </Section>
      )}

      {ev.flaky_tests.length > 0 && (
        <Section title="Flaky Tests" testId="td-flaky-tests">
          <BulletList items={ev.flaky_tests} colour="#eab308" />
        </Section>
      )}

      {ev.regression_tests.length > 0 && (
        <Section title="Regression Tests" testId="td-regression-tests">
          <BulletList items={ev.regression_tests} colour="#f97316" />
        </Section>
      )}
    </>
  );
}

function InfraDrill({ ev }: { ev: InfraEvidence }) {
  return (
    <>
      {ev.dockerfile_issues.length > 0 && (
        <Section title="Dockerfile Issues" defaultOpen testId="td-dockerfile-issues">
          <BulletList items={ev.dockerfile_issues} colour="#f97316" />
        </Section>
      )}
      {ev.ci_config_issues.length > 0 && (
        <Section title="CI Config Issues" testId="td-ci-config-issues">
          <BulletList items={ev.ci_config_issues} colour="#f97316" />
        </Section>
      )}
      {ev.env_var_issues.length > 0 && (
        <Section title="Env Var Issues" testId="td-env-var-issues">
          <BulletList items={ev.env_var_issues} colour="#eab308" />
        </Section>
      )}
      {ev.image_changes.length > 0 && (
        <Section title="Image Changes" testId="td-image-changes">
          <BulletList items={ev.image_changes} colour="#8b949e" />
        </Section>
      )}
    </>
  );
}

function HistoricalDrill({ ev }: { ev: HistoricalEvidence }) {
  return (
    <>
      <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 4 }}>
        Seen {ev.recurrence_count} time{ev.recurrence_count !== 1 ? 's' : ''}
        {ev.last_seen && <span> · Last: {new Date(ev.last_seen).toLocaleDateString()}</span>}
      </div>

      {ev.known_fix && (
        <div
          data-testid="td-known-fix"
          style={{
            fontSize: 11,
            color: '#22c55e',
            background: 'rgba(34,197,94,0.07)',
            border: '1px solid rgba(34,197,94,0.2)',
            borderRadius: 5,
            padding: '6px 8px',
            marginBottom: 6,
          }}
        >
          <strong>Known fix:</strong> {ev.known_fix}
        </div>
      )}

      {ev.similar_failures.length > 0 && (
        <Section title="Similar Past Failures" testId="td-similar-failures">
          {ev.similar_failures.map((f, i) => (
            <div key={i} style={{ marginBottom: 6, fontSize: 11, color: '#8b949e' }}>
              <div style={{ color: '#c9d1d9' }}>{f.run_id}</div>
              <div>{new Date(f.date).toLocaleDateString()} · {Math.round(f.similarity_score * 100)}% similar</div>
              {f.root_cause && <div style={{ color: '#57606a', fontStyle: 'italic' }}>{f.root_cause}</div>}
            </div>
          ))}
        </Section>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// TechnicalDrill — public export
// ---------------------------------------------------------------------------

export interface TechnicalDrillProps {
  evidence: AnyEvidence;
}

export function TechnicalDrill({ evidence }: TechnicalDrillProps) {
  return (
    <div
      data-testid="technical-drill"
      data-evidence-id={evidence.evidence_id}
      data-evidence-type={evidence.evidence_type}
      style={{
        background: '#0d0d14',
        border: '1px solid #1e2030',
        borderRadius: 8,
        padding: '10px 12px',
        marginTop: 6,
        fontSize: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: '#57606a',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: 8,
        }}
      >
        Technical Detail · {evidence.evidence_type}
      </div>

      {/* Type-specific content */}
      {evidence.evidence_type === 'failure'    && <FailureDrill    ev={evidence as FailureEvidence} />}
      {evidence.evidence_type === 'change'     && <ChangeDrill     ev={evidence as ChangeEvidence} />}
      {evidence.evidence_type === 'dependency' && <DependencyDrill ev={evidence as DependencyEvidence} />}
      {evidence.evidence_type === 'test'       && <TestDrill       ev={evidence as TestRunEvidence} />}
      {evidence.evidence_type === 'infra'      && <InfraDrill      ev={evidence as InfraEvidence} />}
      {evidence.evidence_type === 'historical' && <HistoricalDrill ev={evidence as HistoricalEvidence} />}
    </div>
  );
}
