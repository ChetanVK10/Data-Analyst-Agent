import React from 'react';
import './Badge.css';

type BadgeVariant = 'default' | 'accent' | 'success' | 'warning' | 'error' | 'outline';
type BadgeSize = 'sm' | 'md';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  dot = false,
  icon,
  className = '',
  ...props
}) => {
  const classes = [
    'ds-badge',
    `ds-badge--${variant}`,
    `ds-badge--${size}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <span className={classes} {...props}>
      {dot && <span className="ds-badge__dot" />}
      {icon && <span className="ds-badge__icon">{icon}</span>}
      {children}
    </span>
  );
};
