import React from 'react';
import './Card.css';

type CardVariant = 'default' | 'elevated' | 'outlined' | 'interactive' | 'inset';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  noBorder?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  padding = 'md',
  noBorder = false,
  className = '',
  ...props
}) => {
  const classes = [
    'ds-card',
    `ds-card--${variant}`,
    `ds-card--pad-${padding}`,
    noBorder && 'ds-card--no-border',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
};

/* ── Card sub-components ── */

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  icon,
  action,
  className = '',
  ...props
}) => (
  <div className={`ds-card__header ${className}`} {...props}>
    <div className="ds-card__header-left">
      {icon && <span className="ds-card__header-icon">{icon}</span>}
      <div>
        <h3 className="ds-card__title">{title}</h3>
        {subtitle && <p className="ds-card__subtitle">{subtitle}</p>}
      </div>
    </div>
    {action && <div className="ds-card__header-action">{action}</div>}
  </div>
);

export const CardBody: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div className={`ds-card__body ${className}`} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div className={`ds-card__footer ${className}`} {...props}>
    {children}
  </div>
);
