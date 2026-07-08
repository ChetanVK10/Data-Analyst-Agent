import React from 'react';
import { Sparkles, RefreshCw, AlertTriangle, Loader2 } from 'lucide-react';
import { useAnalytics } from '../hooks/useAnalytics';
import { AnalyticsKpis } from '../components/analytics/AnalyticsKpis';
import { AnalyticsCharts } from '../components/analytics/AnalyticsCharts';
import { RecentExecutionsTable } from '../components/analytics/RecentExecutionsTable';
import type { HistoricalReport } from '../types/index';

interface AnalyticsProps {
  sessionQueries?: HistoricalReport[];
  sessionId?: string;
}

export const Analytics: React.FC<AnalyticsProps> = ({ sessionQueries = [], sessionId }) => {
  const { metrics, computed, loading, error, refresh } = useAnalytics();

  return (
    <div className="flex h-full w-full flex-col bg-background text-foreground">
      {/* Header */}
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/70 px-6 py-3 backdrop-blur-xl">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Workspace</div>
          <h1 className="text-sm font-semibold sm:text-base flex items-center gap-2">
            Analytics
            <button 
              onClick={refresh} 
              disabled={loading}
              className="p-1 hover:bg-muted rounded-md transition-colors disabled:opacity-50"
              title="Refresh Analytics"
            >
              <RefreshCw size={14} className={loading ? "animate-spin text-muted-foreground" : "text-muted-foreground"} />
            </button>
          </h1>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
          <Sparkles className="h-3 w-3" /> Last 30 days
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-6xl space-y-6 px-6 py-8">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">Overview</div>
            <h2 className="mt-1 text-2xl font-bold tracking-tight">Everything your agent did this month</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              A live pulse of query volume, latency, and success rates across your DataAgent Pro workspace.
            </p>
          </div>

          {/* Loading State */}
          {loading && metrics.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 space-y-4 animate-in fade-in duration-500">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground font-medium">Fetching workspace analytics...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                <AlertTriangle className="h-6 w-6 text-destructive" />
              </div>
              <h3 className="text-lg font-semibold mb-1">Failed to load analytics</h3>
              <p className="text-sm text-muted-foreground max-w-sm mb-6">{error}</p>
              <button 
                onClick={refresh}
                className="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring bg-primary text-primary-foreground shadow hover:bg-primary/90 h-9 px-4 py-2"
              >
                <RefreshCw size={14} /> Retry
              </button>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && metrics.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 text-center glass-card rounded-2xl">
              <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                <Sparkles className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold mb-1">No analytics available yet</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Run a few analyses to populate this dashboard with insights and execution trends.
              </p>
            </div>
          )}

          {/* Data State */}
          {!loading && !error && computed && metrics.length > 0 && (
            <div className="animate-in fade-in duration-500">
              <AnalyticsKpis computed={computed} />
              <AnalyticsCharts metrics={metrics} computed={computed} />
              <RecentExecutionsTable sessionQueries={sessionQueries} sessionId={sessionId} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
