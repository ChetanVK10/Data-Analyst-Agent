import React from 'react';
import './Table.css';

/* ── Table Root ── */
interface TableProps extends React.HTMLAttributes<HTMLDivElement> {
  compact?: boolean;
}

export const Table: React.FC<TableProps> = ({
  children,
  compact = false,
  className = '',
  ...props
}) => (
  <div className={`ds-table-wrapper ${className}`} {...props}>
    <table className={`ds-table ${compact ? 'ds-table--compact' : ''}`}>
      {children}
    </table>
  </div>
);

/* ── THead ── */
export const THead: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({
  children,
  ...props
}) => (
  <thead className="ds-table__head" {...props}>{children}</thead>
);

/* ── TBody ── */
export const TBody: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({
  children,
  ...props
}) => (
  <tbody className="ds-table__body" {...props}>{children}</tbody>
);

/* ── Tr ── */
interface TrProps extends React.HTMLAttributes<HTMLTableRowElement> {
  hoverable?: boolean;
}

export const Tr: React.FC<TrProps> = ({
  children,
  hoverable = true,
  className = '',
  ...props
}) => (
  <tr className={`ds-table__row ${hoverable ? 'ds-table__row--hoverable' : ''} ${className}`} {...props}>
    {children}
  </tr>
);

/* ── Th ── */
interface ThProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  align?: 'left' | 'center' | 'right';
}

export const Th: React.FC<ThProps> = ({
  children,
  align = 'left',
  className = '',
  ...props
}) => (
  <th className={`ds-table__th ds-table__th--${align} ${className}`} {...props}>
    {children}
  </th>
);

/* ── Td ── */
interface TdProps extends React.TdHTMLAttributes<HTMLTableCellElement> {
  mono?: boolean;
  muted?: boolean;
  align?: 'left' | 'center' | 'right';
}

export const Td: React.FC<TdProps> = ({
  children,
  mono = false,
  muted = false,
  align = 'left',
  className = '',
  ...props
}) => (
  <td
    className={`ds-table__td ds-table__td--${align} ${mono ? 'ds-table__td--mono' : ''} ${muted ? 'ds-table__td--muted' : ''} ${className}`}
    {...props}
  >
    {children}
  </td>
);
