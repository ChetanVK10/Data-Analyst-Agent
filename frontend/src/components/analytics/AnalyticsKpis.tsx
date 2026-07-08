import React from 'react';
import { Activity, Zap, TrendingUp, AlertTriangle } from 'lucide-react';
import type { ComputedMetrics } from '../../services/analytics';

interface AnalyticsKpisProps {
  computed: ComputedMetrics;
}

export const AnalyticsKpis: React.FC<AnalyticsKpisProps> = ({ computed }) => {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi 
          icon={Activity} 
          label="Total Queries" 
          value={computed.totalExecutions.toLocaleString()} 
          delta="Lifetime" 
          positive={true} 
        />
        <Kpi 
          icon={TrendingUp} 
          label="Success Rate" 
          value={`${computed.successRate.toFixed(1)}%`} 
          delta="First Try + Retries" 
          positive={computed.successRate > 80} 
        />
        <Kpi 
          icon={Zap} 
          label="First-Try Rate" 
          value={`${computed.firstTryRate.toFixed(1)}%`} 
          delta="Zero retries" 
          positive={computed.firstTryRate > 70} 
        />
        <Kpi 
          icon={AlertTriangle} 
          label="Failed Queries" 
          value={computed.failed.toLocaleString()} 
          delta="Unrecoverable" 
          positive={computed.failed === 0} 
        />
      </div>

      <section className="glass-card rounded-2xl p-5 mt-4">
        <div>
          <h3 className="text-sm font-semibold tracking-tight">Execution stats</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">Aggregated across all time.</p>
        </div>
        <div className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            <Mini label="Total Recovered" value={computed.retrySuccess.toString()} />
            <Mini label="Recovery Rate" value={`${computed.recoveryRate.toFixed(1)}%`} />
            <Mini label="First Try Success" value={computed.firstTrySuccess.toString()} />
            <Mini label="Unrecoverable" value={computed.failed.toString()} />
          </div>
        </div>
      </section>
    </>
  );
};

function Kpi({ icon: Icon, label, value, delta, positive }: { icon: typeof Activity; label: string; value: string; delta: string; positive?: boolean }) {
  return (
    <div className="glass-card rounded-2xl p-4">
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
        <div className="grid h-7 w-7 place-items-center rounded-lg bg-primary/15 text-primary">
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>
      <div className="mt-2 text-2xl font-bold tracking-tight">{value}</div>
      <div className={"mt-0.5 text-[11px] font-medium " + (positive ?? true ? "text-success" : "text-destructive")}>{delta}</div>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-background/40 p-3">
      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-bold">{value}</div>
    </div>
  );
}
