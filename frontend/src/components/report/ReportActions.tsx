import { useState } from 'react';
import { Check, Copy, Download, FileDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from '@/lib/toast';
import type { AppReportPayload } from './Report';

interface ReportActionsProps {
  payload: AppReportPayload;
}

export function ReportActions({ payload }: ReportActionsProps) {
  const [copied, setCopied] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const [pdfActive, setPdfActive] = useState(false);

  const hasTable = (payload.report.tables?.length ?? 0) > 0;

  // ── PDF ─────────────────────────────────────────────────────────────────────
  const handlePDF = () => {
    setPdfActive(true);
    toast('Opening print dialog...', 'info');
    setTimeout(() => {
      window.print();
      setPdfActive(false);
    }, 500);
  };

  // ── CSV ─────────────────────────────────────────────────────────────────────
  const handleCSV = () => {
    if (!hasTable) return;
    const table = payload.report.tables[0];
    const header = table.columns.join(',');
    const rows = table.rows.map((row) =>
      row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${payload.report.title || 'report'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    setDownloaded(true);
    toast('CSV downloaded', 'success');
    setTimeout(() => setDownloaded(false), 2000);
  };

  // ── Copy ─────────────────────────────────────────────────────────────────────
  const handleCopy = async () => {
    const r = payload.report;
    const lines: string[] = [
      `# ${r.title}`,
      '',
      `## Summary`,
      r.executive_summary?.headline ?? '',
      r.executive_summary?.summary ?? '',
    ];
    if (r.insights?.length) {
      lines.push('', '## Key Insights');
      r.insights.forEach((i) => lines.push(`- **${i.title}**: ${i.body}`));
    }
    if (r.recommendations?.length) {
      lines.push('', '## Recommendations');
      r.recommendations.forEach((rec) => lines.push(`- **${rec.title}**: ${rec.body}`));
    }
    if (payload.debug?.generated_sql) {
      lines.push('', '## Executed SQL', '```sql', payload.debug.generated_sql, '```');
    }
    try {
      await navigator.clipboard.writeText(lines.filter(Boolean).join('\n'));
      setCopied(true);
      toast('Copied to clipboard', 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast('Failed to copy — check clipboard permissions', 'error');
    }
  };

  return (
    <div className="mt-4 flex items-center gap-1.5 flex-wrap">
      <ActionButton 
        icon={pdfActive ? Check : FileDown} 
        label={pdfActive ? 'Opening print dialog...' : 'PDF'} 
        onClick={handlePDF} 
        active={pdfActive}
        title="Save as PDF" 
      />
      <ActionButton
        icon={downloaded ? Check : Download}
        label={downloaded ? '✓ Downloaded' : 'CSV'}
        onClick={handleCSV}
        disabled={!hasTable}
        active={downloaded}
        title={hasTable ? 'Download CSV' : 'No table data'}
      />
      <ActionButton
        icon={copied ? Check : Copy}
        label={copied ? '✓ Copied' : 'Copy'}
        onClick={handleCopy}
        active={copied}
        title="Copy report as Markdown"
      />
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  title,
  active,
}: {
  icon: typeof Copy;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition-all',
        'disabled:cursor-not-allowed disabled:opacity-40',
        active
          ? 'border-success/40 bg-success/10 text-success'
          : 'border-border bg-background/40 text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground',
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}
