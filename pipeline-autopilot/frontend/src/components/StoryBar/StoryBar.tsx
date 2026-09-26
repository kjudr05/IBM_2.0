/**
 * StoryBar — top progress strip showing all 12 story states.
 *
 * Task 10: minimal placeholder that renders and TypeScript-compiles cleanly.
 * Task 12: full implementation with current step highlighted.
 * Runtime fix: labels always visible, not clipped, proportional segments.
 */

import { STORY_STEPS, type StoryState } from '../../state/storyMachine';
import { usePipelineStore } from '../../state/pipelineStore';

export function StoryBar() {
  const storyState = usePipelineStore((s) => s.storyState);
  const currentIndex = STORY_STEPS.find((s) => s.state === storyState)?.index ?? 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        padding: '0 8px',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {STORY_STEPS.map((step) => {
        const isActive = step.state === storyState;
        const isPast = step.index < currentIndex;
        return (
          <div
            key={step.state}
            title={`${step.label}: ${step.caption}`}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              minWidth: 0,
              gap: 2,
              padding: '0 2px',
            }}
          >
            {/* Progress segment */}
            <div
              style={{
                width: '100%',
                height: 3,
                borderRadius: 2,
                background: isActive
                  ? '#3b82d4'
                  : isPast
                  ? '#2a4a6a'
                  : '#1e2030',
                transition: 'background 0.3s',
                flexShrink: 0,
              }}
            />
            {/* Label — always shown but muted when inactive */}
            <span
              style={{
                fontSize: 9,
                lineHeight: 1,
                color: isActive ? '#3b82d4' : isPast ? '#3b5a7a' : '#2a2a4a',
                fontFamily: 'system-ui, sans-serif',
                fontWeight: isActive ? 700 : 400,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: '100%',
                transition: 'color 0.3s',
              }}
            >
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export type { StoryState };
