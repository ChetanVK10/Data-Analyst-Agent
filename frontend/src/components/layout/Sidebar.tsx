import React, { useState } from 'react';
import {
  Database,
  Search,
  Plus,
  Sparkles,
  MessageSquare,
  BarChart3,
  Table2,
  Hash,
  Type,
  Calendar,
  CircleCheck,
  ChevronDown,
  ChevronRight,
  Upload,
  Sigma,
  HelpCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Column } from '@/types/index';

interface HistoryItem { id: string; question: string; success: boolean; duration: number; ts: string; }

interface SidebarProps {
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
  activePath?: '/analytics' | '/';
}

const formatRows = (n: number) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(n);

const dtypeInfo = (dtype: string): { icon: React.ElementType; className: string; shortLabel: string } => {
  const t = dtype.toUpperCase();
  if (/INT|LONG|BYTE/i.test(t))            return { icon: Hash,           className: 'text-sky-400',     shortLabel: 'INT'     };
  if (/CHAR|TEXT|VARCHAR|STRING/i.test(t)) return { icon: Type,           className: 'text-emerald-400', shortLabel: 'STR'     };
  if (/DATE|TIME|TIMESTAMP/i.test(t))      return { icon: Calendar,       className: 'text-amber-400',   shortLabel: 'DATE'    };
  if (/FLOAT|DOUBLE|DECIMAL|NUMERIC/i.test(t)) return { icon: Sigma,      className: 'text-pink-400',    shortLabel: 'NUM'     };
  return                                          { icon: HelpCircle,      className: 'text-zinc-500',    shortLabel: dtype.slice(0, 4) };
};

export function Sidebar({
  hasDataset, datasetName, rowCount = 0, columns = [], history = [],
  onUpload, onSelectHistory, selectedHistoryId, isCollapsed, onToggleCollapse, activePath = '/'
}: SidebarProps) {
  const [schemaOpen, setSchemaOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCols = columns.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isCollapsed) {
    return (
      <aside className="flex flex-col items-center py-4 gap-4 w-14 shrink-0 border-r border-border bg-sidebar text-sidebar-foreground transition-all duration-300">
        <button
          onClick={onToggleCollapse}
          className="w-9 h-9 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent border border-transparent hover:border-border transition-all cursor-pointer focus-ring"
          title="Expand sidebar"
        >
          <ChevronRight size={15} />
        </button>
        <div className="w-6 h-px bg-border" aria-hidden="true" />
        <button
          onClick={onUpload}
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-primary/15 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/20 hover:border-primary/30 transition-all cursor-pointer focus-ring"
          title="New Analysis"
        >
          <Upload size={14} />
        </button>
        {hasDataset && (
          <button
            className="w-9 h-9 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-all cursor-pointer"
            title="Schema"
          >
            <Database size={14} />
          </button>
        )}
      </aside>
    );
  }

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground transition-all duration-300">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 pt-5 pb-4">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-[image:var(--gradient-primary)] shadow-[var(--shadow-glow)]">
          <Sparkles className="h-4 w-4 text-primary-foreground" />
        </div>
        <div className="min-w-0 flex-1 flex items-center justify-between">
          <div>
            <div className="truncate text-sm font-semibold tracking-tight">DataAgent Pro</div>
            <div className="truncate text-[11px] text-muted-foreground">Autonomous analyst</div>
          </div>
          <button
            onClick={onToggleCollapse}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
          >
            <ChevronDown className="h-4 w-4 rotate-90" />
          </button>
        </div>
      </div>

      {/* New analysis */}
      <div className="px-4">
        <button 
          onClick={onUpload}
          className="group flex w-full items-center justify-between rounded-xl border border-border bg-[image:var(--gradient-primary)] px-3 py-2.5 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)] transition-transform hover:scale-[1.01] active:scale-[0.99] focus-ring cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            New analysis
          </span>
          <kbd className="rounded-md bg-black/20 px-1.5 py-0.5 text-[10px] font-medium tracking-wider">⌘K</kbd>
        </button>
      </div>

      {/* Dataset card */}
      <div className="px-4 pt-4">
        {hasDataset ? (
          <div className="glass-card rounded-xl p-3.5">
            <div className="flex items-center gap-2">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-secondary">
                <Database className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-semibold">{datasetName}</div>
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <CircleCheck className="h-3 w-3 text-success" />
                  Connected
                </div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-lg border border-border bg-background/40 px-2 py-1.5">
                <div className="text-muted-foreground">Rows</div>
                <div className="font-semibold">{formatRows(rowCount)}</div>
              </div>
              <div className="rounded-lg border border-border bg-background/40 px-2 py-1.5">
                <div className="text-muted-foreground">Columns</div>
                <div className="font-semibold">{columns.length}</div>
              </div>
            </div>
          </div>
        ) : (
          <button
            onClick={onUpload}
            className="w-full rounded-2xl border border-dashed border-border bg-secondary/10 hover:bg-secondary/20 hover:border-primary/20 p-5 text-center transition-all cursor-pointer group focus-ring"
          >
            <div className="w-9 h-9 rounded-xl bg-background border border-border flex items-center justify-center mx-auto mb-3 group-hover:border-primary/20 group-hover:bg-primary/5 transition-all">
              <Upload size={14} className="text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <p className="text-[12px] font-semibold text-foreground group-hover:text-primary transition-colors">Upload a CSV file</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">Click or drag and drop</p>
          </button>
        )}
      </div>

      {/* Schema */}
      {hasDataset && (
        <div className="px-4 pt-4">
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setSchemaOpen((v) => !v)}
              className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <Table2 className="h-3 w-3" /> Schema
              <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", schemaOpen ? "" : "-rotate-90")} />
            </button>
            <span className="badge badge-neutral">{columns.length}</span>
          </div>
          
          {schemaOpen && (
            <div className="animate-fade-in bg-background/30 rounded-xl border border-border overflow-hidden">
              <div className="p-2 border-b border-border">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
                  <input
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search columns…"
                    className="w-full rounded-md border border-border bg-secondary/40 py-1.5 pl-7 pr-2 text-[11px] text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/25"
                  />
                </div>
              </div>
              <div className="max-h-[160px] overflow-y-auto scrollbar-thin">
                {filteredCols.length === 0 ? (
                  <div className="p-3 text-center text-[10px] text-muted-foreground">No columns found</div>
                ) : (
                  <div className="p-1">
                    {filteredCols.map((c) => {
                      const { icon: Icon, className: iconClass, shortLabel } = dtypeInfo(c.dtype);
                      return (
                        <div
                          key={c.name}
                          className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-sidebar-accent"
                        >
                          <span className="flex min-w-0 items-center gap-2">
                            <Icon className={cn("h-3 w-3 shrink-0", iconClass)} />
                            <span className="truncate font-mono text-[11px] text-foreground">{c.name}</span>
                          </span>
                          <span className="shrink-0 text-[9px] text-muted-foreground ml-2">{shortLabel}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Threads */}
      <div className="mt-5 flex min-h-0 flex-1 flex-col px-4">
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            <MessageSquare className="h-3 w-3" /> Recent
          </div>
          {history.length > 0 && <span className="badge badge-neutral">{history.length}</span>}
        </div>
        
        <div className="scrollbar-thin min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-1 pb-4">
          {history.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-secondary/10 py-6 flex flex-col items-center justify-center gap-2 text-center mt-2">
              <MessageSquare size={14} className="text-muted-foreground" />
              <p className="text-[11px] text-foreground font-medium">No conversations yet</p>
            </div>
          ) : (
            history.map((c) => {
              const active = selectedHistoryId === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => onSelectHistory(c.id)}
                  className={cn(
                    "block w-full rounded-lg px-2.5 py-2 text-left transition-colors relative overflow-hidden group cursor-pointer",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "hover:bg-sidebar-accent/60 text-muted-foreground hover:text-foreground",
                  )}
                >
                  <div className={cn(
                    "absolute left-0 top-0 bottom-0 w-0.5",
                    active ? "bg-primary" : c.success ? "bg-transparent group-hover:bg-primary/20" : "bg-destructive/40"
                  )} />
                  <div className="truncate text-[12px] font-medium">{c.question}</div>
                  <div className="mt-0.5 flex items-center justify-between text-[10px] text-muted-foreground/80">
                    <span>{c.ts}</span>
                    <span>{(c.duration / 1000).toFixed(1)}s</span>
                  </div>
                </button>
              )
            })
          )}
        </div>
      </div>

      {/* Footer nav */}
      <div className="border-t border-border p-3">
        <button
          className={cn(
            "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium cursor-pointer",
            activePath === "/analytics"
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
          )}
        >
          <BarChart3 className="h-3.5 w-3.5" /> Analytics
        </button>
        <button
          className={cn(
            "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium cursor-pointer",
            activePath === "/"
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
          )}
        >
          <Sparkles className="h-3.5 w-3.5" /> Workspace
        </button>
      </div>
    </aside>
  );
}
