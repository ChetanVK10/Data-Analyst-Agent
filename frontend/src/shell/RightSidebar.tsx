import React from 'react';
import {
  CheckCircle2, XCircle, Loader2, ChevronRight, ChevronLeft,
  Activity, Zap, Clock, RotateCcw, Rows3, Cpu, CircleDot,
  ArrowRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

/* ── Types ── */
interface TraceStep {
  node: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  duration_ms?: number;
  details?: string;
}

interface RecentActivityItem {
  id: string;
  question: string;
  ts: string;
  success: boolean;
  model?: string;
}

interface RightSidebarProps {
  trace?: TraceStep[];
  isAnalyzing?: boolean;
  recentActivity?: RecentActivityItem[];
  sessionId?: string;
  isOpen: boolean;
  onToggleOpen: () => void;
  activeModel?: string;
  activeExecutionTime?: number;
  activeRetryCount?: number;
  activeRowCount?: number;
  activeStatus?: boolean;
}

/* ── KV Row ── */
const KVRow: React.FC<{
  label: string;
  icon: React.ElementType;
  value: React.ReactNode;
}> = ({ label, icon: Icon, value }) => (
  <div className="flex items-center justify-between py-2.5 border-b border-white/[0.04] last:border-b-0">
    <div className="flex items-center gap-2 text-[12px] text-[#6B6B80]">
      <Icon size={12} className="shrink-0" />
      <span className="font-medium">{label}</span>
    </div>
    <div className="text-[12px] font-semibold text-[#A0A0B0]">{value}</div>
  </div>
);

/* ─────────────────────────────────── */
export const RightSidebar: React.FC<RightSidebarProps> = ({
  trace = [], isAnalyzing = false, recentActivity = [], isOpen, onToggleOpen,
  activeModel = 'Llama 3 (Groq)', activeExecutionTime, activeRetryCount,
  activeRowCount, activeStatus
}) => {

  /* ── Collapsed icon rail ── */
  if (!isOpen) {
    return (
      <aside
        className="flex flex-col items-center py-4 gap-4 w-14 shrink-0 border-l border-white/[0.06] bg-[#08080E] transition-all duration-300"
        aria-label="Collapsed run details"
      >
        <button
          onClick={onToggleOpen}
          className="w-9 h-9 rounded-xl flex items-center justify-center text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] border border-transparent hover:border-white/[0.06] transition-all cursor-pointer focus-ring"
          aria-label="Expand run details"
        >
          <ChevronLeft size={15} />
        </button>
        <div className="w-6 h-px bg-white/[0.06]" aria-hidden="true" />
        <button
          onClick={onToggleOpen}
          className="w-9 h-9 rounded-xl flex items-center justify-center text-[#6B6B80] hover:text-violet-400 hover:bg-white/[0.05] transition-all relative cursor-pointer"
          title="Run Details"
          aria-label="View run details"
        >
          <Activity size={14} />
          {isAnalyzing && (
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
          )}
        </button>
      </aside>
    );
  }

  /* ── Expanded sidebar ── */
  return (
    <aside
      className="flex flex-col h-full w-[256px] shrink-0 border-l border-white/[0.06] bg-[#08080E] overflow-hidden transition-all duration-300 animate-fade-in"
      aria-label="Run details panel"
    >
      <div className="flex flex-col h-full min-h-0">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 pt-4 pb-3">
          <div className="flex items-center gap-2">
            <Activity size={13} className="text-[#6B6B80]" />
            <span className="text-[13px] font-semibold text-[#A0A0B0]">Run Details</span>
            {isAnalyzing && (
              <span className="badge badge-accent text-[9px] animate-pulse">LIVE</span>
            )}
          </div>
          <button
            onClick={onToggleOpen}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] border border-white/[0.06] transition-all cursor-pointer focus-ring"
            aria-label="Collapse run details"
          >
            <ChevronRight size={14} />
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div className="flex flex-col flex-1 min-h-0 overflow-y-auto px-3 pb-4 space-y-4" style={{ scrollbarWidth: 'thin' }}>

          {/* ── Execution Metrics Card ── */}
          <section>
            <div className="section-label px-1 mb-2.5">
              <Cpu size={11} />
              Execution
            </div>

            <div className="rounded-2xl border border-white/[0.07] bg-[#12121A] px-3 py-1">
              {/* Model */}
              <KVRow
                label="Model"
                icon={Cpu}
                value={<span className="badge badge-accent text-[10px]">{activeModel}</span>}
              />

              {/* Status */}
              <KVRow
                label="Status"
                icon={CircleDot}
                value={
                  isAnalyzing ? (
                    <span className="badge badge-accent text-[10px] gap-1">
                      <Loader2 size={9} className="animate-spin" />
                      Running
                    </span>
                  ) : activeStatus !== undefined ? (
                    <span className={cn('badge text-[10px]', activeStatus ? 'badge-success' : 'badge-error')}>
                      {activeStatus ? (
                        <><CheckCircle2 size={9} /> Succeeded</>
                      ) : (
                        <><XCircle size={9} /> Failed</>
                      )}
                    </span>
                  ) : (
                    <span className="text-[#46465A] font-medium">—</span>
                  )
                }
              />

              {/* Time Taken */}
              <KVRow
                label="Time Taken"
                icon={Clock}
                value={
                  activeExecutionTime !== undefined ? (
                    <span className="font-mono text-[#F4F4F8]">
                      {(activeExecutionTime / 1000).toFixed(2)}s
                    </span>
                  ) : <span className="text-[#46465A]">—</span>
                }
              />

              {/* Retries */}
              <KVRow
                label="Retries"
                icon={RotateCcw}
                value={
                  activeRetryCount !== undefined ? (
                    <span className={cn('font-mono', activeRetryCount > 0 ? 'text-amber-400' : 'text-[#A0A0B0]')}>
                      {activeRetryCount} / 3
                    </span>
                  ) : <span className="text-[#46465A]">—</span>
                }
              />

              {/* Rows Returned */}
              <KVRow
                label="Rows"
                icon={Rows3}
                value={
                  activeRowCount !== undefined ? (
                    <span className="font-mono text-[#F4F4F8]">{activeRowCount.toLocaleString()}</span>
                  ) : <span className="text-[#46465A]">—</span>
                }
              />
            </div>
          </section>

          {/* ── Agent Pipeline Nodes (live) ── */}
          {isAnalyzing && trace.length > 0 && (
            <section className="animate-fade-in">
              <div className="section-label px-1 mb-2.5">
                <Zap size={11} />
                Pipeline
              </div>

              <div className="rounded-2xl border border-white/[0.07] bg-[#12121A] overflow-hidden">
                {trace.slice(0, 5).map((step, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      'flex items-center gap-2.5 px-3 py-2.5 transition-colors',
                      idx !== 0 && 'border-t border-white/[0.04]'
                    )}
                  >
                    <div className={cn(
                      'w-1.5 h-1.5 rounded-full shrink-0',
                      step.status === 'running' && 'bg-violet-400 animate-pulse',
                      step.status === 'success' && 'bg-emerald-500',
                      step.status === 'failed'  && 'bg-red-500',
                      step.status === 'pending' && 'bg-white/[0.15]',
                      step.status === 'skipped' && 'bg-white/[0.10]',
                    )} />
                    <span className="text-[11.5px] text-[#A0A0B0] font-medium flex-1 truncate">{step.node}</span>
                    {step.duration_ms && (
                      <span className="text-[10px] font-mono text-[#6B6B80] shrink-0">
                        {step.duration_ms}ms
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Recent Activity ── */}
          <section className="flex-1 flex flex-col">
            <div className="section-label px-1 mb-2.5">
              <Clock size={11} />
              Recent Activity
              {recentActivity.length > 0 && (
                <span className="ml-auto badge badge-neutral text-[10px]">{recentActivity.length}</span>
              )}
            </div>

            {recentActivity.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/[0.05] bg-white/[0.01] py-8 flex flex-col items-center justify-center gap-2 text-center">
                <Zap size={15} className="text-[#46465A]" />
                <p className="text-[11.5px] text-[#6B6B80] font-medium">No activity yet</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {recentActivity.slice(0, 6).map(item => (
                  <div
                    key={item.id}
                    className="rounded-xl bg-[#12121A] border border-white/[0.05] p-3 hover:border-white/[0.09] hover:bg-[#14141E] transition-all"
                  >
                    <div className="flex items-start gap-2">
                      {item.success
                        ? <CheckCircle2 size={11} className="text-emerald-500 mt-0.5 shrink-0" />
                        : <XCircle     size={11} className="text-red-500 mt-0.5 shrink-0" />
                      }
                      <p className="text-[11.5px] text-[#A0A0B0] font-medium leading-snug line-clamp-2 flex-1">
                        {item.question}
                      </p>
                    </div>
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.04]">
                      <span className="text-[10px] text-[#46465A]">{item.ts}</span>
                      <div className="flex items-center gap-1 text-[10px] text-[#46465A]">
                        <ArrowRight size={9} />
                        <span>{item.model || 'Llama 3'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </aside>
  );
};

export default RightSidebar;
