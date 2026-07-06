import React from 'react';
import './Spinner.css';

type SpinnerSize = 'sm' | 'md' | 'lg';

interface SpinnerProps {
  size?: SpinnerSize;
  label?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  label,
}) => (
  <div className={`ds-spinner ds-spinner--${size}`} role="status" aria-label={label || 'Loading'}>
    <div className="ds-spinner__ring" />
    {label && <span className="ds-spinner__label">{label}</span>}
  </div>
);


/* ── ThinkingDots — AI thinking indicator ── */
export const ThinkingDots: React.FC = () => (
  <span className="ds-thinking" aria-label="AI is thinking">
    <span className="ds-thinking__dot" style={{ animationDelay: '0ms' }} />
    <span className="ds-thinking__dot" style={{ animationDelay: '150ms' }} />
    <span className="ds-thinking__dot" style={{ animationDelay: '300ms' }} />
  </span>
);
