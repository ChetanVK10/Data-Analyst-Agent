import { useState } from "react";
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
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Column, HistoricalReport } from "@/types/index";

interface AppSidebarProps {
  hasDataset: boolean;
  datasetName?: string;
  rowCount?: number;
  columns?: Column[];
  history: HistoricalReport[];
  onUpload: () => void;
  onSelectHistory: (id: string) => void;
  selectedHistoryId?: string;
  activePath: string;
  setActivePath: (path: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const getIconForType = (type: string) => {
  if (type.includes("int") || type.includes("float") || type.includes("numeric")) return Hash;
  if (type.includes("date") || type.includes("time")) return Calendar;
  return Type;
};

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  if (diffMs < 0) return 'Just now';
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export function AppSidebar({
  hasDataset,
  datasetName,
  rowCount,
  columns,
  history,
  onUpload,
  onSelectHistory,
  selectedHistoryId,
  activePath,
  setActivePath,
  isCollapsed,
  onToggleCollapse,
}: AppSidebarProps) {
  const [schemaOpen, setSchemaOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredColumns = columns?.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? [];

  return (
    <aside
      className={cn(
        "flex h-screen shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground transition-[width] duration-300 ease-in-out overflow-hidden",
        isCollapsed ? "w-0 border-r-0" : "w-72"
      )}
    >
      <div className="flex min-h-0 flex-1 flex-col" style={{ width: "18rem" }}>
        {/* ── Sticky top section ── */}
        <div className="shrink-0">
          {/* Brand + collapse toggle */}
          <div className="flex items-center justify-between px-4 pt-4 pb-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[image:var(--gradient-primary)] shadow-[var(--shadow-glow)]">
                <Sparkles className="h-4 w-4 text-primary-foreground" />
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold tracking-tight">DataAgent Pro</div>
                <div className="truncate text-[11px] text-muted-foreground">Autonomous analyst</div>
              </div>
            </div>
            <button
              onClick={onToggleCollapse}
              className="ml-2 grid h-7 w-7 shrink-0 place-items-center rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-foreground transition-colors"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>

          {/* New analysis button */}
          <div className="px-4 pb-3">
            <button
              onClick={onUpload}
              className="group flex w-full items-center justify-between rounded-xl border border-border bg-[image:var(--gradient-primary)] px-3 py-2.5 text-sm font-medium text-primary-foreground shadow-[var(--shadow-glow)] transition-transform hover:scale-[1.01] active:scale-[0.99]"
            >
              <span className="flex items-center gap-2">
                <Plus className="h-4 w-4" />
                New analysis
              </span>
              <kbd className="rounded-md bg-black/20 px-1.5 py-0.5 text-[10px] font-medium tracking-wider">⌘K</kbd>
            </button>
          </div>

          {/* Dataset card — sticky */}
          {hasDataset && (
            <div className="px-4 pb-3">
              <div className="glass-card rounded-xl p-3">
                <div className="flex items-center gap-2">
                  <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-secondary">
                    <Database className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-semibold">{datasetName || "dataset.csv"}</div>
                    <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <CircleCheck className="h-3 w-3 text-success" />
                      Connected
                    </div>
                  </div>
                </div>
                <div className="mt-2.5 grid grid-cols-2 gap-2 text-[11px]">
                  <div className="rounded-lg border border-border bg-background/40 px-2 py-1.5">
                    <div className="text-muted-foreground">Rows</div>
                    <div className="font-semibold">{rowCount?.toLocaleString() || 0}</div>
                  </div>
                  <div className="rounded-lg border border-border bg-background/40 px-2 py-1.5">
                    <div className="text-muted-foreground">Columns</div>
                    <div className="font-semibold">{columns?.length || 0}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Scrollable middle section ── */}
        <div className="scrollbar-thin flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-4">
          {/* Schema */}
          {hasDataset && columns && columns.length > 0 && (
            <div className="shrink-0">
              {/* Schema search */}
              {schemaOpen && (
                <div className="relative mb-2">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search columns…"
                    className="w-full rounded-lg border border-border bg-secondary/40 py-1.5 pl-7 pr-2.5 text-[11px] text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/25"
                  />
                </div>
              )}

              <button
                onClick={() => setSchemaOpen((v) => !v)}
                className="flex w-full items-center justify-between py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground hover:text-foreground"
              >
                <span className="flex items-center gap-1.5">
                  <Table2 className="h-3 w-3" /> Schema ({columns.length})
                </span>
                <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", schemaOpen ? "" : "-rotate-90")} />
              </button>

              {schemaOpen && (
                <div className="mb-2 space-y-0.5 animate-fade-in">
                  {filteredColumns.map((c) => {
                    const Icon = getIconForType(c.dtype);
                    return (
                      <div
                        key={c.name}
                        className="flex items-center justify-between rounded-md px-2 py-1.5 text-xs hover:bg-sidebar-accent"
                      >
                        <span className="flex min-w-0 items-center gap-2">
                          <Icon className="h-3 w-3 shrink-0 text-muted-foreground" />
                          <span className="truncate font-mono text-[11px]">{c.name}</span>
                        </span>
                        <span className="ml-2 shrink-0 text-[10px] text-muted-foreground">{c.dtype}</span>
                      </div>
                    );
                  })}
                  {filteredColumns.length === 0 && (
                    <div className="py-3 text-center text-[11px] text-muted-foreground">No columns match</div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* History */}
          <div className="flex-1">
            <button
              onClick={() => setHistoryOpen((v) => !v)}
              className="flex w-full items-center justify-between py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground hover:text-foreground"
            >
              <span className="flex items-center gap-1.5">
                <MessageSquare className="h-3 w-3" /> Recent
              </span>
              <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", historyOpen ? "" : "-rotate-90")} />
            </button>

            {historyOpen && (
              <div className="space-y-0.5 pb-2">
                {history.length === 0 ? (
                  <div className="py-4 text-center text-[11px] text-muted-foreground opacity-60">
                    No history yet
                  </div>
                ) : (
                  history.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => onSelectHistory(c.id.toString())}
                      className={cn(
                        "block w-full rounded-lg px-2.5 py-2.5 text-left transition-colors group",
                        selectedHistoryId === c.id.toString()
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "hover:bg-sidebar-accent/60"
                      )}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <div className="truncate text-xs font-medium leading-snug">{c.question}</div>
                        {c.success !== undefined && (
                          <div className={cn(
                            "mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full",
                            c.success ? "bg-success" : "bg-destructive"
                          )} />
                        )}
                      </div>
                      <div className="mt-0.5 text-[10px] text-muted-foreground">
                        {c.created_at ? formatRelativeTime(String(c.created_at)) : ""}
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Footer nav ── */}
        <div className="shrink-0 border-t border-border p-3 space-y-0.5">
          <button
            onClick={() => setActivePath("/")}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium transition-colors",
              activePath === "/"
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
            )}
          >
            <Sparkles className="h-3.5 w-3.5" /> Workspace
          </button>
          <button
            onClick={() => setActivePath("/analytics")}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium transition-colors",
              activePath === "/analytics"
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground"
            )}
          >
            <BarChart3 className="h-3.5 w-3.5" /> Analytics
          </button>
        </div>
      </div>
    </aside>
  );
}