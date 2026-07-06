import React from 'react';
import './ChartContainer.css';

interface ChartContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  minHeight?: string;
  loading?: boolean;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  children,
  title,
  subtitle,
  minHeight = '380px',
  loading = false,
  className = '',
  ...props
}) => (
  <div className={`ds-chart ${className}`} {...props}>
    {(title || subtitle) && (
      <div className="ds-chart__header">
        {title && <h4 className="ds-chart__title">{title}</h4>}
        {subtitle && <p className="ds-chart__subtitle">{subtitle}</p>}
      </div>
    )}
    <div className="ds-chart__canvas" style={{ minHeight }}>
      {loading ? (
        <div className="ds-chart__loading">
          <div className="ds-chart__loading-ring" />
          <span>Rendering visualization...</span>
        </div>
      ) : (
        children
      )}
    </div>
  </div>
);
