/**
 * StoryBar — top progress strip showing all 12 story states.
 *
 * Task 10: minimal placeholder that renders and TypeScript-compiles cleanly.
 * Task 12: full implementation with current step highlighted.
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
        gap: 4,
        padding: '0 16px',
        height: '100%',
      }}
    >
      {STORY_STEPS.map((step) => {
        const isActive = step.state === storyState;
        const isPast = step.index < currentIndex;
        return (
          <div
            key={step.state}
            title={step.caption}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              background: isActive
                ? '#3b82d4'
                : isPast
                ? '#2a4a6a'
                : '#1e2030',
              transition: 'background 0.3s',
              position: 'relative',
            }}
          >
            {isActive && (
              <span
                style={{
                  position: 'absolute',
                  top: 8,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  fontSize: 10,
                  color: '#3b82d4',
                  whiteSpace: 'nowrap',
                  fontFamily: 'system-ui, sans-serif',
                }}
              >
                {step.label}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export type { StoryState };
