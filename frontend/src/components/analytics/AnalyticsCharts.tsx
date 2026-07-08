import React from 'react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis
} from 'recharts';
import type { MetricDay } from '../../types/index';
import type { ComputedMetrics } from '../../services/analytics';

interface AnalyticsChartsProps {
  metrics: MetricDay[];
  computed: ComputedMetrics;
}

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ metrics, computed }) => {
  // Sort metrics ascending for time-series charts
  const timeSeriesData = [...metrics].sort((a, b) => new Date(a.execution_date).getTime() - new Date(b.execution_date).getTime());

  // 1. Query Volume
  const queryVolumeData = timeSeriesData.map(m => ({
    date: new Date(m.execution_date).toLocaleDateString([], { month: 'short', day: 'numeric' }),
    queries: m.total_executions
  }));

  // 2. Success vs Failure Trend
  const successTrendData = timeSeriesData.map(m => ({
    date: new Date(m.execution_date).toLocaleDateString([], { month: 'short', day: 'numeric' }),
    success: m.first_try_success_count + m.retry_success_count,
    failed: m.failed_count
  }));

  // 3. Failure Mix
  const failureMixData = Object.entries(computed.failureAggregates).map(([type, count]) => ({
    name: type,
    count
  })).sort((a, b) => b.count - a.count);

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-3">
      {/* Query Volume */}
      <Panel className="lg:col-span-2" title="Query volume" caption="Daily queries over time.">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={queryVolumeData} margin={{ left: -20, right: 8, top: 8 }}>
              <defs>
                <linearGradient id="qv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" stroke="var(--color-muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--color-muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="queries" stroke="var(--color-primary)" strokeWidth={2} fill="url(#qv)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      {/* Failure Mix */}
      <Panel title="Failure Mix" caption="Common error classifications.">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={failureMixData} margin={{ left: -20, right: 8, top: 8 }}>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" stroke="var(--color-muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--color-muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} 
                cursor={{ fill: "var(--color-secondary)", opacity: 0.4 }} 
              />
              <Bar dataKey="count" fill="var(--color-destructive)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      {/* Success vs Failure Trend */}
      <Panel className="lg:col-span-3" title="Success vs Failure Trend" caption="Daily breakdown of successful and failed executions.">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={successTrendData} margin={{ left: -20, right: 8, top: 8 }}>
              <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" stroke="var(--color-muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--color-muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="success" stroke="var(--color-success)" strokeWidth={2} dot={{ r: 3, fill: "var(--color-success)" }} name="Successful" />
              <Line type="monotone" dataKey="failed" stroke="var(--color-destructive)" strokeWidth={2} dot={{ r: 3, fill: "var(--color-destructive)" }} name="Failed" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
};

function Panel({ children, title, caption, className = "" }: { children: React.ReactNode; title: string; caption: string; className?: string }) {
  return (
    <section className={"glass-card rounded-2xl p-5 " + className}>
      <div>
        <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{caption}</p>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}
