import React, { forwardRef } from 'react';
import './Input.css';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  inputSize?: 'md' | 'lg';
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  label,
  hint,
  error,
  icon,
  iconRight,
  inputSize = 'md',
  className = '',
  id,
  ...props
}, ref) => {
  const inputId = id || `input-${Math.random().toString(36).slice(2, 8)}`;

  return (
    <div className={`ds-input-group ${error ? 'ds-input-group--error' : ''} ${className}`}>
      {label && (
        <label htmlFor={inputId} className="ds-input-label">{label}</label>
      )}
      <div className={`ds-input-wrapper ds-input-wrapper--${inputSize}`}>
        {icon && <span className="ds-input-icon ds-input-icon--left">{icon}</span>}
        <input
          ref={ref}
          id={inputId}
          className={`ds-input ${icon ? 'ds-input--has-icon-left' : ''} ${iconRight ? 'ds-input--has-icon-right' : ''}`}
          {...props}
        />
        {iconRight && <span className="ds-input-icon ds-input-icon--right">{iconRight}</span>}
      </div>
      {hint && !error && <p className="ds-input-hint">{hint}</p>}
      {error && <p className="ds-input-error">{error}</p>}
    </div>
  );
});

Input.displayName = 'Input';


/* ── Textarea variant ── */
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({
  label,
  hint,
  error,
  className = '',
  id,
  ...props
}, ref) => {
  const textareaId = id || `textarea-${Math.random().toString(36).slice(2, 8)}`;

  return (
    <div className={`ds-input-group ${error ? 'ds-input-group--error' : ''} ${className}`}>
      {label && (
        <label htmlFor={textareaId} className="ds-input-label">{label}</label>
      )}
      <textarea
        ref={ref}
        id={textareaId}
        className="ds-textarea"
        {...props}
      />
      {hint && !error && <p className="ds-input-hint">{hint}</p>}
      {error && <p className="ds-input-error">{error}</p>}
    </div>
  );
});

Textarea.displayName = 'Textarea';
