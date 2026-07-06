import React, { useRef, useEffect, useState } from 'react';
import {
  Send, Download, Sparkles, User, Loader2,
  Search, TrendingUp, Lightbulb, CheckCircle2,
  Code2, Copy, ChevronDown, ChevronUp,
  FileDown, Table2, BarChart2, Zap, ArrowUpRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Plotly from 'plotly.js-dist-min';
import PlotlyChart from '../components/PlotlyChart';
import { CodeBlock } from '../design-system';

/* ══════════════════════════════════════════════════════════════
   TYPED PROPS — mirror backend schemas.py exactly.
   No free-form strings, no parsing, no markdown splitting.
══════════════════════════════════════════════════════════════ */

export interface ExecutiveSummary {
  headline:   string;
  summary:    string;
  confidence: 'High' | 'Medium' | 'Low';
}

export interface TableResult {
  title:   string;
  columns: string[];
  rows:    any[][];
}

export interface ChartSpec {
  title:       string;
  type:        string;
  plotly_json: any;
}

export interface Insight        { title: string; body: string; }
export interface Recommendation { title: string; body: string; }

export interface ReportSection {
  title:             string;
  executive_summary: ExecutiveSummary;
  tables:            TableResult[];
  charts:            ChartSpec[];
  insights:          Insight[];
  recommendations:   Recommendation[];
}

export interface DebugInfo {
  generated_sql:  string | null;
  execution_plan: string | null;
  llm_reasoning:  string | null;
}

export interface ChatMessage {
  id:            string;
  role:          'user' | 'assistant';
  content?:      string;        // user messages
  report?:       ReportSection; // assistant messages — single source of truth
  debug?:        DebugInfo;
  success?:      boolean;
  executionId?:  number | null;
  executionTime?: number;
  retryCount?:   number;
  model?:        string;
  provider?:     string;
}

interface ChatWorkspaceProps {
  messages:         ChatMessage[];
  question:         string;
  isAnalyzing:      boolean;
  onQuestionChange: (q: string) => void;
  onSubmit:         (e: React.FormEvent) => void;
  hasDataset:       boolean;
}

/* ══════════════════════════════════════════════════════════════
   SECTION HEADING
══════════════════════════════════════════════════════════════ */
const SectionHeading: React.FC<{
  icon:       React.ElementType;
  label:      string;
  iconColor?: string;
  badge?:     React.ReactNode;
}> = ({ icon: Icon, label, iconColor = 'text-[#6B6B80]', badge }) => (
  <div className="flex items-center gap-2.5 mb-4">
    <div className="w-6 h-6 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center shrink-0">
      <Icon size={12} className={iconColor} />
    </div>
    <span className="text-[13px] font-semibold text-[#A0A0B0] tracking-tight">{label}</span>
    {badge}
  </div>
);

/* ══════════════════════════════════════════════════════════════
   1. EXECUTIVE SUMMARY
   Highest visual priority — full headline + narrative.
══════════════════════════════════════════════════════════════ */
const ExecutiveSummarySection: React.FC<{ summary: ExecutiveSummary }> = ({ summary }) => {
  const confidenceColor = {
    High:   'badge-success',
    Medium: 'badge-warning',
    Low:    'badge-error',
  }[summary.confidence] ?? 'badge-neutral';

  return (
    <div className="report-section report-section-primary">
      <div className="flex items-start justify-between mb-4 gap-4">
        <SectionHeading icon={Sparkles} label="Executive Summary" iconColor="text-violet-400" />
        <span className={cn('badge text-[10px] shrink-0 mt-0.5', confidenceColor)}>
          {summary.confidence} Confidence
        </span>
      </div>
      {/* Headline — direct answer in large type */}
      <p className="text-[15px] font-semibold text-white leading-snug mb-3">
        {summary.headline}
      </p>
      {/* Narrative — paragraph(s), no markdown parsing needed */}
      {summary.summary.split('\n\n').map((para, i) => (
        <p key={i} className="text-[13.5px] text-[#C8C8D8] leading-[1.8] mb-2 last:mb-0">
          {para.trim()}
        </p>
      ))}
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
   2. RESULTS TABLE
   Full rows with search, sort, pagination, CSV export.
══════════════════════════════════════════════════════════════ */
const ResultsTableSection: React.FC<{ table: TableResult }> = ({ table }) => {
  const [search,  setSearch]  = useState('');
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page,    setPage]    = useState(1);
  const perPage = 7;

  const filtered = table.rows.filter(row =>
    row.some(cell => String(cell ?? '').toLowerCase().includes(search.toLowerCase()))
  );

  const sorted = [...filtered].sort((a, b) => {
    if (!sortCol) return 0;
    const ci = table.columns.indexOf(sortCol);
    const av = a[ci], bv = b[ci];
    if (av === null) return 1;
    if (bv === null) return -1;
    const cmp = typeof av === 'number' && typeof bv === 'number'
      ? av - bv
      : String(av).localeCompare(String(bv));
    return sortDir === 'asc' ? cmp : -cmp;
  });

  useEffect(() => setPage(1), [search]);

  const totalPages = Math.ceil(sorted.length / perPage);
  const paginated  = sorted.slice((page - 1) * perPage, page * perPage);

  const handleExport = () => {
    const csv = [
      table.columns.map(c => `"${c}"`).join(','),
      ...table.rows.map(row =>
        row.map(c => `"${c === null ? '' : String(c).replace(/"/g, '""')}"`).join(',')
      )
    ].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a   = Object.assign(document.createElement('a'), { href: url, download: `${table.title}.csv` });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="report-section report-section-secondary">
      <div className="flex items-center justify-between mb-4">
        <SectionHeading
          icon={Table2}
          label={table.title}
          iconColor="text-sky-400"
          badge={<span className="badge badge-neutral text-[10px]">{table.rows.length} rows</span>}
        />
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 px-3 h-7 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-[11px] text-[#6B6B80] hover:text-[#A0A0B0] transition-all cursor-pointer font-medium"
          aria-label="Export as CSV"
        >
          <FileDown size={11} /> Export CSV
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-3 max-w-xs">
        <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#46465A]" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search results…"
          className="w-full pl-7 pr-3 h-7 rounded-lg bg-white/[0.03] border border-white/[0.06] focus:border-violet-500/30 text-[11.5px] text-[#A0A0B0] placeholder:text-[#46465A] outline-none transition-colors"
          aria-label="Filter table"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-white/[0.07] overflow-hidden bg-[#0D0D15]">
        <div className="overflow-x-auto max-h-[280px]">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 z-10 bg-[#12121A] border-b border-white/[0.07]">
              <tr>
                {table.columns.map(col => (
                  <th
                    key={col}
                    onClick={() => {
                      setSortDir(d => sortCol === col ? (d === 'asc' ? 'desc' : 'asc') : 'asc');
                      setSortCol(col);
                    }}
                    className="px-4 py-2.5 text-[10.5px] font-bold text-[#6B6B80] uppercase tracking-wider cursor-pointer hover:text-[#A0A0B0] select-none whitespace-nowrap group transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col}</span>
                      <span className={cn(sortCol === col ? 'text-violet-400' : 'text-[#46465A] group-hover:text-[#6B6B80]')}>
                        {sortCol === col ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={table.columns.length} className="px-4 py-8 text-center text-[12px] text-[#46465A]">
                    No results found
                  </td>
                </tr>
              ) : paginated.map((row, ri) => (
                <tr
                  key={ri}
                  className={cn('transition-colors hover:bg-violet-500/[0.04]', ri % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.015]')}
                >
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className={cn(
                        'px-4 py-2.5 text-[12.5px] border-r border-white/[0.03] last:border-r-0 whitespace-nowrap',
                        typeof cell === 'number' ? 'font-mono text-[#F4F4F8] font-medium' : 'text-[#A0A0B0]',
                        cell === null && 'text-[#46465A] italic'
                      )}
                    >
                      {cell === null ? 'NULL' : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {sorted.length > perPage && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-white/[0.06] bg-[#12121A]/50">
            <span className="text-[11px] text-[#6B6B80]">
              Showing{' '}
              <strong className="text-[#A0A0B0]">{(page - 1) * perPage + 1}</strong>–
              <strong className="text-[#A0A0B0]">{Math.min(page * perPage, sorted.length)}</strong>
              {' '}of{' '}
              <strong className="text-[#A0A0B0]">{sorted.length}</strong>
            </span>
            <div className="flex items-center gap-1.5">
              {['Prev', 'Next'].map((label, i) => (
                <button
                  key={label}
                  onClick={() => setPage(p => p + (i === 0 ? -1 : 1))}
                  disabled={i === 0 ? page === 1 : page === totalPages}
                  className="px-2.5 h-6 rounded-md bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.07] disabled:opacity-35 disabled:cursor-not-allowed text-[11px] text-[#6B6B80] hover:text-[#A0A0B0] transition-all cursor-pointer"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
   3. CHART SECTION
   Reads directly from ChartSpec.plotly_json — no separate chartJson prop.
══════════════════════════════════════════════════════════════ */
const ChartSection: React.FC<{ chart: ChartSpec; chartId: string }> = ({ chart, chartId }) => {
  const handleExport = () => {
    const el = document.getElementById(chartId);
    if (el) Plotly.downloadImage(el as any, { format: 'png', filename: chartId });
  };

  return (
    <div className="report-section report-section-secondary">
      <div className="flex items-center justify-between mb-4">
        <SectionHeading icon={BarChart2} label={chart.title} iconColor="text-indigo-400" />
        <button
          onClick={handleExport}
          className="mb-4 flex items-center gap-1.5 px-3 h-7 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.07] text-[11px] text-[#6B6B80] hover:text-[#A0A0B0] transition-all cursor-pointer font-medium"
          aria-label="Export chart as PNG"
        >
          <Download size={10} /> Export PNG
        </button>
      </div>
      <div className="rounded-xl overflow-hidden border border-white/[0.06]">
        <PlotlyChart chartData={chart.plotly_json} chartId={chartId} />
      </div>
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
   4. INSIGHTS
══════════════════════════════════════════════════════════════ */
const InsightsSection: React.FC<{ insights: Insight[] }> = ({ insights }) => (
  <div className="report-section report-section-secondary">
    <SectionHeading icon={TrendingUp} label="Key Insights" iconColor="text-emerald-400" />
    <div className="grid grid-cols-1 gap-2.5">
      {insights.map((insight, i) => (
        <div
          key={i}
          className="flex items-start gap-3 p-3.5 rounded-xl bg-emerald-500/[0.04] border border-emerald-500/[0.12] hover:border-emerald-500/25 transition-all"
        >
          <div className="w-5 h-5 rounded-md bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
            <TrendingUp size={10} className="text-emerald-400" />
          </div>
          <div className="flex-1">
            <p className="text-[12px] font-bold text-emerald-300 mb-1">{insight.title}</p>
            <p className="text-[12.5px] text-[#C8C8D8] leading-relaxed">{insight.body}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   5. RECOMMENDATIONS
══════════════════════════════════════════════════════════════ */
const RecommendationsSection: React.FC<{ recommendations: Recommendation[] }> = ({ recommendations }) => (
  <div className="report-section report-section-tertiary">
    <SectionHeading icon={Lightbulb} label="Recommendations" iconColor="text-amber-400" />
    <div className="grid grid-cols-1 gap-2.5">
      {recommendations.map((rec, i) => (
        <div
          key={i}
          className="flex items-start gap-3 p-3.5 rounded-xl bg-amber-500/[0.04] border border-amber-500/[0.12] hover:border-amber-500/25 transition-all"
        >
          <div className="w-5 h-5 rounded-md bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
            <ArrowUpRight size={10} className="text-amber-400" />
          </div>
          <div className="flex-1">
            <p className="text-[12px] font-bold text-amber-300 mb-1">{rec.title}</p>
            <p className="text-[12.5px] text-[#C8C8D8] leading-relaxed">{rec.body}</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   6. DEBUG / SQL VIEWER
   Reads from DebugInfo — not from report section.
══════════════════════════════════════════════════════════════ */
const DebugSection: React.FC<{ debug: DebugInfo }> = ({ debug }) => {
  const [open,   setOpen]   = useState(false);
  const [copied, setCopied] = useState(false);

  if (!debug.generated_sql && !debug.execution_plan && !debug.llm_reasoning) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(debug.generated_sql || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="report-section report-section-tertiary">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center justify-between w-full group mb-0"
        aria-expanded={open}
        aria-label="Toggle debug panel"
      >
        <SectionHeading icon={Code2} label="Debug · SQL &amp; Reasoning" iconColor="text-sky-400" />
        <div className="flex items-center gap-2 mb-4">
          <span className="text-[11px] text-[#6B6B80] group-hover:text-[#A0A0B0] transition-colors font-medium">
            {open ? 'Hide' : 'Show'}
          </span>
          {open ? <ChevronUp size={13} className="text-[#6B6B80]" /> : <ChevronDown size={13} className="text-[#6B6B80]" />}
        </div>
      </button>

      {open && (
        <div className="animate-fade-up space-y-3">
          {debug.generated_sql && (
            <div className="relative rounded-xl overflow-hidden border border-white/[0.07] bg-[#0A0A12]">
              <div className="absolute top-2.5 right-2.5 z-10">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2.5 h-6 rounded-md bg-white/[0.06] hover:bg-white/[0.10] border border-white/[0.08] text-[10.5px] text-[#6B6B80] hover:text-[#A0A0B0] transition-all cursor-pointer font-medium"
                  aria-label="Copy SQL"
                >
                  <Copy size={9} /> {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <CodeBlock language="sql" title="Generated SQL">
                {debug.generated_sql}
              </CodeBlock>
            </div>
          )}

          {debug.execution_plan && (
            <div className="rounded-xl border border-white/[0.07] bg-[#0A0A12] px-4 py-3">
              <p className="text-[10px] font-bold text-[#6B6B80] uppercase tracking-wider mb-2">Execution Plan</p>
              <pre className="text-[11.5px] text-[#A0A0B0] whitespace-pre-wrap font-mono leading-relaxed">
                {debug.execution_plan}
              </pre>
            </div>
          )}

          {debug.llm_reasoning && (
            <div className="rounded-xl border border-white/[0.07] bg-[#0A0A12] px-4 py-3">
              <p className="text-[10px] font-bold text-[#6B6B80] uppercase tracking-wider mb-2">LLM Reasoning</p>
              <p className="text-[11.5px] text-[#A0A0B0] leading-relaxed">{debug.llm_reasoning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
   7. METADATA BADGES + ACTION TOOLBAR
══════════════════════════════════════════════════════════════ */
const ReportFooter: React.FC<{
  msg: ChatMessage;
  onCopyResponse: () => void;
  onDownloadCsv:  () => void;
}> = ({ msg, onCopyResponse, onDownloadCsv }) => {
  const hasCsv = (msg.report?.tables?.length ?? 0) > 0;
  return (
    <>
      {/* Metadata */}
      <div className="flex flex-wrap items-center gap-2 px-6 py-3 border-t border-white/[0.05] bg-white/[0.01]">
        <span className="badge badge-accent text-[10px]">
          <Zap size={9} /> {msg.provider || 'Groq'} · {msg.model || 'Llama 3'}
        </span>
        {msg.executionTime !== undefined && (
          <span className="badge badge-neutral text-[10px]">⏱ {(msg.executionTime / 1000).toFixed(2)}s</span>
        )}
        {(msg.retryCount ?? 0) > 0 && (
          <span className="badge badge-warning text-[10px]">↺ {msg.retryCount} retries</span>
        )}
        {(msg.report?.tables?.[0]?.rows?.length ?? 0) > 0 && (
          <span className="badge badge-neutral text-[10px]">
            ⊞ {msg.report!.tables[0].rows.length.toLocaleString()} rows
          </span>
        )}
        <span className={cn('badge text-[10px]', msg.success ? 'badge-success' : 'badge-error')}>
          {msg.success ? '✓ Success' : '✗ Failed'}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 px-6 py-4 bg-white/[0.01] border-t border-white/[0.05]">
        {msg.executionId && (
          <a
            href={`http://localhost:8000/report/${msg.executionId}/pdf`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3.5 h-8 rounded-xl bg-violet-600/10 hover:bg-violet-600 text-violet-400 hover:text-white border border-violet-500/20 hover:border-violet-500/30 text-[11.5px] font-semibold transition-all cursor-pointer"
          >
            <Download size={11} /> PDF Report
          </a>
        )}
        {hasCsv && (
          <button
            onClick={onDownloadCsv}
            className="flex items-center gap-1.5 px-3.5 h-8 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.07] text-[11.5px] text-[#6B6B80] hover:text-[#A0A0B0] font-semibold transition-all cursor-pointer"
            aria-label="Download CSV"
          >
            <FileDown size={11} /> CSV
          </button>
        )}
        <button
          onClick={onCopyResponse}
          className="flex items-center gap-1.5 px-3.5 h-8 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.07] text-[11.5px] text-[#6B6B80] hover:text-[#A0A0B0] font-semibold transition-all cursor-pointer"
          aria-label="Copy response"
        >
          <Copy size={11} /> Copy
        </button>
      </div>
    </>
  );
};

/* ══════════════════════════════════════════════════════════════
   REPORT CARD — assembles all sub-sections
   No parsing. No markdown. Every section reads typed props.
══════════════════════════════════════════════════════════════ */
const ReportCard: React.FC<{ msg: ChatMessage }> = ({ msg }) => {
  const report = msg.report;
  if (!report) return null;

  const handleCopyResponse = () => {
    const lines = [
      `REPORT: ${report.title}`,
      `\nHEADLINE: ${report.executive_summary.headline}`,
      `\nSUMMARY:\n${report.executive_summary.summary}`,
      report.insights.length       ? `\nINSIGHTS:\n${report.insights.map((i, n) => `${n+1}. ${i.title}: ${i.body}`).join('\n')}` : '',
      report.recommendations.length ? `\nRECOMMENDATIONS:\n${report.recommendations.map((r, n) => `${n+1}. ${r.title}: ${r.body}`).join('\n')}` : '',
    ].join('');
    navigator.clipboard.writeText(lines);
  };

  const handleDownloadCsv = () => {
    const tbl = report.tables[0];
    if (!tbl) return;
    const csv = [
      tbl.columns.map(c => `"${c}"`).join(','),
      ...tbl.rows.map(row =>
        row.map(c => `"${c === null ? '' : String(c).replace(/"/g, '""')}"`).join(',')
      )
    ].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a   = Object.assign(document.createElement('a'), { href: url, download: `${report.title}.csv` });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#12121A] overflow-hidden shadow-lg animate-fade-up">
      {/* Status Header */}
      <div className="flex items-center justify-between px-6 py-3.5 bg-white/[0.015] border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className={cn(
            'w-2 h-2 rounded-full',
            msg.success !== false
              ? 'bg-emerald-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]'
              : 'bg-red-500'
          )} />
          <span className={cn(
            'text-[12.5px] font-bold tracking-wide',
            msg.success !== false ? 'text-emerald-400' : 'text-red-400'
          )}>
            {msg.success !== false ? report.title : 'Analysis Failed'}
          </span>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-[#6B6B80]">
          <span>Model: <strong className="text-[#A0A0B0]">{msg.model || 'Llama 3 (Groq)'}</strong></span>
          {msg.executionTime && <span>{(msg.executionTime / 1000).toFixed(2)}s</span>}
          {(msg.retryCount ?? 0) > 0 && <span className="text-amber-400">{msg.retryCount} retries</span>}
        </div>
      </div>

      {/* ── Eye-flow: Summary → Tables → Charts → Insights → Recommendations → Debug ── */}

      {/* 1. Executive Summary */}
      <ExecutiveSummarySection summary={report.executive_summary} />

      {/* 2. Result Tables */}
      {report.tables.map((tbl, i) => (
        <ResultsTableSection key={i} table={tbl} />
      ))}

      {/* 3. Charts — reads plotly_json from ChartSpec directly */}
      {report.charts.map((chart, i) => (
        <ChartSection
          key={i}
          chart={chart}
          chartId={`chart-${msg.id}-${i}`}
        />
      ))}

      {/* 4. Insights */}
      {report.insights.length > 0 && (
        <InsightsSection insights={report.insights} />
      )}

      {/* 5. Recommendations */}
      {report.recommendations.length > 0 && (
        <RecommendationsSection recommendations={report.recommendations} />
      )}

      {/* 6. Debug — SQL, plan, reasoning (collapsed by default) */}
      {msg.debug && <DebugSection debug={msg.debug} />}

      {/* 7. Footer — badges + actions */}
      <ReportFooter
        msg={msg}
        onCopyResponse={handleCopyResponse}
        onDownloadCsv={handleDownloadCsv}
      />
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
   USER BUBBLE
══════════════════════════════════════════════════════════════ */
const UserBubble: React.FC<{ content: string }> = ({ content }) => (
  <div className="flex justify-end animate-fade-up">
    <div className="flex items-end gap-2.5 max-w-[72%]">
      <div className="bg-gradient-to-br from-violet-600 to-violet-700 text-white rounded-2xl rounded-br-md px-4 py-3 text-[13.5px] leading-relaxed shadow-[0_4px_20px_rgba(139,92,246,0.25)]">
        {content}
      </div>
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0 mb-0.5 shadow-[0_0_10px_rgba(139,92,246,0.3)]">
        <User size={13} className="text-white" />
      </div>
    </div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   ASSISTANT BUBBLE
══════════════════════════════════════════════════════════════ */
const AssistantBubble: React.FC<{ msg: ChatMessage }> = ({ msg }) => (
  <div className="flex items-start gap-3.5 w-full animate-fade-up">
    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/10 border border-violet-500/20 flex items-center justify-center shrink-0 mt-0.5 shadow-[0_0_12px_rgba(139,92,246,0.15)]">
      <Sparkles size={13} className="text-violet-400" />
    </div>
    <div className="flex-1 min-w-0">
      <ReportCard msg={msg} />
    </div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   THINKING INDICATOR
══════════════════════════════════════════════════════════════ */
const ThinkingBubble: React.FC = () => (
  <div className="flex items-start gap-3.5 animate-fade-in">
    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/10 border border-violet-500/20 flex items-center justify-center shrink-0">
      <Sparkles size={13} className="text-violet-400 animate-pulse" />
    </div>
    <div className="rounded-2xl rounded-tl-md border border-white/[0.08] bg-[#12121A] px-5 py-3.5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 dot-1" />
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 dot-2" />
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 dot-3" />
        </div>
        <span className="text-[12.5px] text-[#6B6B80] font-medium">Analyzing your data…</span>
      </div>
    </div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   WELCOME SCREEN
══════════════════════════════════════════════════════════════ */
const EXAMPLE_PROMPTS = [
  'Show total revenue grouped by country',
  'What are the top 10 products by sales?',
  'Plot monthly revenue trend as a line chart',
  'Average units sold per region this year',
];

const WelcomeScreen: React.FC<{
  hasDataset:      boolean;
  onPromptSelect: (p: string) => void;
}> = ({ hasDataset, onPromptSelect }) => (
  <div className="flex flex-col items-center justify-center h-full gap-8 px-8 text-center py-16 animate-fade-in">
    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500/15 to-indigo-500/10 border border-violet-500/20 flex items-center justify-center shadow-[0_0_32px_rgba(139,92,246,0.15)]">
      <Sparkles size={26} className="text-violet-400" />
    </div>

    <div className="space-y-2">
      <h2 className="text-[22px] font-bold text-white tracking-tight">
        {hasDataset ? 'Ask anything about your data' : 'Start with your data'}
      </h2>
      <p className="text-[13.5px] text-[#6B6B80] leading-relaxed max-w-sm mx-auto">
        {hasDataset
          ? 'Ask questions in natural language. The AI agent will query your dataset and return a structured report.'
          : 'Upload a CSV file to begin.'}
      </p>
    </div>

    {hasDataset && (
      <div className="w-full max-w-md space-y-2">
        <p className="text-[11px] font-bold text-[#46465A] uppercase tracking-widest mb-3">Try asking</p>
        {EXAMPLE_PROMPTS.map(prompt => (
          <button
            key={prompt}
            onClick={() => onPromptSelect(prompt)}
            className="w-full text-left px-4 py-3 rounded-xl bg-white/[0.02] border border-white/[0.06] text-[13px] text-[#A0A0B0] hover:text-[#F4F4F8] hover:border-violet-500/25 hover:bg-violet-500/[0.04] transition-all duration-150 group cursor-pointer"
            aria-label={`Use prompt: ${prompt}`}
          >
            <div className="flex items-center justify-between">
              <span>"{prompt}"</span>
              <Sparkles size={11} className="text-[#46465A] group-hover:text-violet-400 transition-colors shrink-0 ml-2" />
            </div>
          </button>
        ))}
      </div>
    )}

    <div className="flex flex-wrap items-center justify-center gap-2 mt-2">
      {['DuckDB In-Memory', 'Auto SQL Generation', 'Plotly Charts', 'AI Insights', 'PDF Reports'].map(f => (
        <span key={f} className="badge badge-neutral text-[10.5px]">{f}</span>
      ))}
    </div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   MAIN: CHAT WORKSPACE
══════════════════════════════════════════════════════════════ */
export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  messages, question, isAnalyzing, onQuestionChange, onSubmit, hasDataset
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAnalyzing]);

  const isEmpty = messages.length === 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit(e as any);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#08080E]">
      {/* Scrollable message canvas */}
      <div className="flex-1 overflow-y-auto min-h-0" style={{ scrollbarWidth: 'thin' }}>
        {isEmpty && !isAnalyzing ? (
          <WelcomeScreen hasDataset={hasDataset} onPromptSelect={onQuestionChange} />
        ) : (
          <div className="max-w-[900px] w-full mx-auto px-6 py-8 space-y-8">
            {messages.map(msg => (
              <div key={msg.id}>
                {msg.role === 'user'
                  ? <UserBubble content={msg.content || ''} />
                  : <AssistantBubble msg={msg} />
                }
              </div>
            ))}
            {isAnalyzing && <ThinkingBubble />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 px-6 pb-5 pt-3 border-t border-white/[0.05] bg-[#08080E]">
        <form onSubmit={onSubmit} className="max-w-[900px] w-full mx-auto">
          <div className={cn(
            'flex items-end gap-3 rounded-2xl border px-4 py-3 transition-all',
            hasDataset && !isAnalyzing
              ? 'bg-[#12121A] border-white/[0.09] hover:border-white/[0.13] focus-within:border-violet-500/40 focus-within:shadow-[0_0_0_3px_rgba(139,92,246,0.08)]'
              : 'bg-[#10101A] border-white/[0.05]'
          )}>
            <Sparkles size={15} className={cn(
              'shrink-0 mb-1 transition-colors',
              hasDataset && !isAnalyzing ? 'text-violet-400/70' : 'text-[#46465A]'
            )} />
            <textarea
              value={question}
              onChange={e => onQuestionChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                !hasDataset   ? 'Upload a CSV file to get started…'
                : isAnalyzing ? 'Agent is analyzing your question…'
                :               'Ask a question about your dataset… (Enter to send)'
              }
              disabled={!hasDataset || isAnalyzing}
              rows={1}
              className="flex-1 bg-transparent text-[13.5px] text-[#F4F4F8] placeholder:text-[#46465A] outline-none resize-none leading-relaxed disabled:opacity-50 disabled:cursor-not-allowed min-h-[22px] max-h-[120px]"
              style={{ scrollbarWidth: 'none' }}
              aria-label="Ask a question about your dataset"
            />
            <button
              type="submit"
              disabled={!hasDataset || isAnalyzing || !question.trim()}
              className={cn(
                'flex items-center justify-center w-8 h-8 rounded-xl transition-all cursor-pointer shrink-0 focus-ring',
                hasDataset && !isAnalyzing && question.trim()
                  ? 'bg-violet-600 hover:bg-violet-500 shadow-[0_0_14px_rgba(139,92,246,0.3)] text-white'
                  : 'bg-white/[0.04] text-[#46465A] cursor-not-allowed'
              )}
              aria-label="Send question"
            >
              {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Send size={13} />}
            </button>
          </div>
          <p className="text-center text-[10.5px] text-[#46465A] mt-2">
            DataAgent can make mistakes. Always verify critical insights.
          </p>
        </form>
      </div>
    </div>
  );
};

export default ChatWorkspace;
