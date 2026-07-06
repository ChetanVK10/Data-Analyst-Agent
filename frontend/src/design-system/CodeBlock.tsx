import React from 'react';
import './CodeBlock.css';

interface CodeBlockProps {
  children: string;
  language?: string;
  title?: string;
  maxHeight?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  children,
  language = 'sql',
  title,
  maxHeight = '320px',
}) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(children);
  };

  return (
    <div className="ds-code-block">
      {(title || language) && (
        <div className="ds-code-block__header">
          <span className="ds-code-block__lang">{title || language.toUpperCase()}</span>
          <button className="ds-code-block__copy" onClick={handleCopy} title="Copy to clipboard">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
            </svg>
          </button>
        </div>
      )}
      <pre className="ds-code-block__pre" style={{ maxHeight }}>
        <code className="ds-code-block__code">{children}</code>
      </pre>
    </div>
  );
};

/* ── Inline Code ── */
export const InlineCode: React.FC<React.HTMLAttributes<HTMLElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <code className={`ds-inline-code ${className}`} {...props}>{children}</code>
);
