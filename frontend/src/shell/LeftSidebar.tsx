import React, { useState } from 'react';
import {
  Upload, Database, ChevronRight, ChevronLeft, CheckCircle2,
  XCircle, Clock, Search, MessageSquare, Plus, TableProperties,
  Hash, Type, Calendar, Sigma, HelpCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ── Types ── */
interface Column { name: string; dtype: string; }
interface HistoryItem { id: string; question: string; success: boolean; duration: number; ts: string; }

interface LeftSidebarProps {
  hasDataset: boolean;
  datasetName?: string;
  rowCount?: number;
  columns?: Column[];
  history?: HistoryItem[];
  onUpload: () => void;
  onSelectHistory: (id: string) => void;
  selectedHistoryId?: string;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

/* ── dtype icon + color ── */
const dtypeInfo = (dtype: string): { icon: React.ElementType; className: string; shortLabel: string } => {
  const t = dtype.toUpperCase();
  if (/INT|LONG|BYTE/i.test(t))            return { icon: Hash,           className: 'text-sky-400',     shortLabel: 'INT'     };
  if (/CHAR|TEXT|VARCHAR|STRING/i.test(t)) return { icon: Type,           className: 'text-emerald-400', shortLabel: 'STR'     };
  if (/DATE|TIME|TIMESTAMP/i.test(t))      return { icon: Calendar,       className: 'text-amber-400',   shortLabel: 'DATE'    };
  if (/FLOAT|DOUBLE|DECIMAL|NUMERIC/i.test(t)) return { icon: Sigma,      className: 'text-pink-400',    shortLabel: 'NUM'     };
  return                                          { icon: HelpCircle,      className: 'text-zinc-500',    shortLabel: dtype.slice(0, 4) };
};

const formatRows = (n: number) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(n);

/* ────────────────────────────────────────────────── */
export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  hasDataset, datasetName, rowCount = 0, columns = [], history = [],
  onUpload, onSelectHistory, selectedHistoryId, isCollapsed, onToggleCollapse
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCols = columns.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  /* ── Collapsed icon rail ── */
  if (isCollapsed) {
    return (
      <aside
        className="flex flex-col items-center py-4 gap-4 w-14 shrink-0 border-r border-white/[0.06] bg-[#08080E] transition-all duration-300"
        aria-label="Collapsed sidebar"
      >
        <button
          onClick={onToggleCollapse}
          className="w-9 h-9 rounded-xl flex items-center justify-center text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] border border-transparent hover:border-white/[0.06] transition-all cursor-pointer focus-ring"
          aria-label="Expand sidebar"
        >
          <ChevronRight size={15} />
        </button>
        <div className="w-6 h-px bg-white/[0.06]" aria-hidden="true" />
        <button
          onClick={onUpload}
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-violet-600/15 text-violet-400 hover:bg-violet-600 hover:text-white border border-violet-500/20 hover:border-violet-500/30 transition-all cursor-pointer focus-ring"
          aria-label="Upload new CSV"
          title="New Analysis"
        >
          <Upload size={14} />
        </button>
        {hasDataset && (
          <button
            className="w-9 h-9 rounded-xl flex items-center justify-center text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] transition-all cursor-pointer"
            title="Schema"
          >
            <Database size={14} />
          </button>
        )}
      </aside>
    );
  }

  /* ── Expanded sidebar ── */
  return (
    <aside
      className="flex flex-col h-full w-[272px] shrink-0 border-r border-white/[0.06] bg-[#08080E] overflow-hidden transition-all duration-300"
      aria-label="Dataset & navigation sidebar"
    >
      <div className="flex flex-col h-full min-h-0 overflow-hidden">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 pt-4 pb-3">
          <button
            onClick={onUpload}
            className="flex-1 flex items-center justify-center gap-2 h-9 rounded-xl bg-violet-600 hover:bg-violet-500 active:bg-violet-700 text-white text-[12.5px] font-semibold transition-all shadow-[0_4px_14px_rgba(139,92,246,0.25)] cursor-pointer focus-ring"
            aria-label="Start new analysis by uploading CSV"
          >
            <Plus size={13} />
            New Analysis
          </button>
          <button
            onClick={onToggleCollapse}
            className="w-9 h-9 ml-2 rounded-xl flex items-center justify-center text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] border border-white/[0.06] transition-all cursor-pointer shrink-0 focus-ring"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft size={14} />
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div className="flex flex-col flex-1 min-h-0 overflow-y-auto px-3 pb-4 space-y-5" style={{ scrollbarWidth: 'thin' }}>

          {/* ── Dataset Card ── */}
          <section aria-label="Dataset information">
            <div className="section-label px-1 mb-2.5">
              <Database size={11} />
              Dataset
            </div>

            {hasDataset ? (
              <div className="rounded-2xl border border-white/[0.08] bg-[#12121A] p-4 space-y-3.5 shadow-sm">
                {/* Name + status */}
                <div className="flex items-start gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/15 flex items-center justify-center shrink-0 mt-0.5">
                    <TableProperties size={13} className="text-violet-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-white truncate leading-tight" title={datasetName}>
                      {datasetName}
                    </p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                      <span className="text-[11px] text-emerald-400 font-medium">Connected</span>
                    </div>
                  </div>
                </div>

                {/* Stats row */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-xl bg-white/[0.03] border border-white/[0.05] px-3 py-2.5 text-center">
                    <span className="block text-[16px] font-bold text-white leading-none">{columns.length}</span>
                    <span className="block text-[10px] text-[#6B6B80] font-medium mt-1 uppercase tracking-wide">Columns</span>
                  </div>
                  <div className="rounded-xl bg-white/[0.03] border border-white/[0.05] px-3 py-2.5 text-center">
                    <span className="block text-[16px] font-bold text-white leading-none">{formatRows(rowCount)}</span>
                    <span className="block text-[10px] text-[#6B6B80] font-medium mt-1 uppercase tracking-wide">Rows</span>
                  </div>
                </div>

                {/* Engine badge */}
                <div className="flex items-center justify-center">
                  <span className="badge badge-neutral text-[10px]">
                    <span className="w-1 h-1 rounded-full bg-emerald-500 mr-0.5" />
                    DuckDB · In-Memory
                  </span>
                </div>
              </div>
            ) : (
              <button
                onClick={onUpload}
                className="w-full rounded-2xl border border-dashed border-white/[0.07] bg-white/[0.01] hover:bg-white/[0.03] hover:border-violet-500/20 p-5 text-center transition-all cursor-pointer group focus-ring"
                aria-label="Upload a CSV file to get started"
              >
                <div className="w-9 h-9 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mx-auto mb-3 group-hover:border-violet-500/20 group-hover:bg-violet-500/5 transition-all">
                  <Upload size={14} className="text-[#46465A] group-hover:text-violet-400 transition-colors" />
                </div>
                <p className="text-[12px] font-semibold text-[#6B6B80] group-hover:text-[#A0A0B0] transition-colors">Upload a CSV file</p>
                <p className="text-[11px] text-[#46465A] mt-0.5">Click or drag and drop</p>
              </button>
            )}
          </section>

          {/* ── Schema Explorer ── */}
          {hasDataset && (
            <section aria-label="Schema explorer">
              <div className="section-label px-1 mb-2.5">
                <Search size={11} />
                Schema Explorer
                <span className="ml-auto badge badge-neutral text-[10px]">{columns.length}</span>
              </div>

              <div className="rounded-2xl border border-white/[0.07] bg-[#12121A] overflow-hidden">
                {/* Search */}
                <div className="p-2.5 border-b border-white/[0.05]">
                  <div className="relative">
                    <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#46465A]" />
                    <input
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      placeholder="Search columns…"
                      className="w-full pl-7 pr-3 h-7 rounded-lg bg-white/[0.03] border border-white/[0.06] focus:border-violet-500/30 focus:bg-white/[0.05] text-[11.5px] text-[#A0A0B0] placeholder:text-[#46465A] outline-none transition-all"
                      aria-label="Filter columns"
                    />
                  </div>
                </div>

                {/* Column list */}
                <div className="max-h-[196px] overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
                  {filteredCols.length === 0 ? (
                    <p className="text-[11px] text-[#46465A] text-center py-4">No columns match</p>
                  ) : (
                    filteredCols.map((col, idx) => {
                      const { icon: DIcon, className: dClass, shortLabel } = dtypeInfo(col.dtype);
                      return (
                        <div
                          key={col.name}
                          className={cn(
                            'flex items-center gap-2.5 px-3 py-2 transition-colors hover:bg-white/[0.03]',
                            idx !== 0 && 'border-t border-white/[0.04]'
                          )}
                        >
                          <DIcon size={12} className={cn(dClass, 'shrink-0')} />
                          <span className="text-[12px] text-[#A0A0B0] truncate flex-1 font-medium" title={col.name}>
                            {col.name}
                          </span>
                          <span className={cn('text-[9.5px] font-bold px-1.5 py-0.5 rounded-md border', dClass,
                            'border-current/20 bg-current/5 opacity-70'
                          )}>
                            {shortLabel}
                          </span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </section>
          )}

          {/* ── Conversation History ── */}
          <section className="flex-1 flex flex-col" aria-label="Conversation history">
            <div className="section-label px-1 mb-2.5">
              <MessageSquare size={11} />
              Conversations
              {history.length > 0 && (
                <span className="ml-auto badge badge-neutral text-[10px]">{history.length}</span>
              )}
            </div>

            {history.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/[0.05] bg-white/[0.01] py-8 flex flex-col items-center justify-center gap-2 text-center">
                <MessageSquare size={16} className="text-[#46465A]" />
                <p className="text-[11.5px] text-[#6B6B80] font-medium">No conversations yet</p>
                <p className="text-[10.5px] text-[#46465A]">Ask a question to get started</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {history.map(item => {
                  const isSelected = selectedHistoryId === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => onSelectHistory(item.id)}
                      className={cn(
                        'w-full text-left rounded-xl p-3 border transition-all duration-150 cursor-pointer group focus-ring block',
                        isSelected
                          ? 'bg-[#14141E] border-violet-500/25 shadow-sm'
                          : 'bg-transparent border-white/[0.04] hover:bg-[#12121A] hover:border-white/[0.08]'
                      )}
                      aria-current={isSelected ? 'true' : undefined}
                    >
                      <div className="flex items-start gap-2">
                        {/* Left accent bar */}
                        <div className={cn(
                          'w-0.5 rounded-full shrink-0 mt-0.5 self-stretch min-h-[28px]',
                          isSelected ? 'bg-violet-500' : item.success ? 'bg-white/[0.08]' : 'bg-red-500/40'
                        )} />
                        <div className="flex-1 min-w-0">
                          <p className={cn(
                            'text-[12px] font-medium leading-snug line-clamp-2',
                            isSelected ? 'text-[#F4F4F8]' : 'text-[#A0A0B0] group-hover:text-[#F4F4F8]'
                          )}>
                            {item.question}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5">
                            {item.success
                              ? <CheckCircle2 size={10} className="text-emerald-500 shrink-0" />
                              : <XCircle     size={10} className="text-red-500 shrink-0" />
                            }
                            <span className="text-[10px] text-[#6B6B80]">{item.ts}</span>
                            <span className="ml-auto text-[10px] text-[#46465A] flex items-center gap-0.5 font-mono">
                              <Clock size={8} />
                              {(item.duration / 1000).toFixed(1)}s
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </aside>
  );
};

export default LeftSidebar;
