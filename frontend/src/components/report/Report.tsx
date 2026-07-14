import React from 'react';
import { ExecutiveSummaryCard } from './ExecutiveSummaryCard';
import { ResultsTableCard } from './ResultsTableCard';
import { ChartCard } from './ChartCard';
import { InsightCards } from './InsightCard';
import { RecommendationCards } from './RecommendationCard';
import { SQLViewer } from './SQLViewer';
import { DebugPanel } from './DebugPanel';
import { ReportActions } from './ReportActions';
import type { ReportSection, DebugInfo } from '@/types/index';

export interface AppReportPayload {
  report: ReportSection;
  debug?: DebugInfo;
}

function DelayedCard({ delay, children }: { delay: number; children: React.ReactNode }) {
  return (
    <div
      className="animate-fade-in"
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}
    >
      {children}
    </div>
  );
}

export function Report({ payload }: { payload: AppReportPayload }) {
  return (
    <div className="space-y-4">
      <DelayedCard delay={0}>
        <ExecutiveSummaryCard payload={payload} />
      </DelayedCard>

      {payload.report.tables?.length > 0 && (
        <DelayedCard delay={80}>
          <ResultsTableCard payload={payload} />
        </DelayedCard>
      )}

      {payload.report.charts?.length > 0 && (
        <DelayedCard delay={160}>
          <div className={payload.report.charts.length === 1 ? '' : 'grid gap-4 lg:grid-cols-2'}>
            {payload.report.charts.map((c, i) => (
              <ChartCard
                key={i}
                chart={c}
                chartId={`chart-${i}-${payload.report.title.replace(/\s/g, '-').slice(0, 20)}`}
              />
            ))}
          </div>
        </DelayedCard>
      )}

      {payload.report.insights?.length > 0 && (
        <DelayedCard delay={240}>
          <InsightCards payload={payload} />
        </DelayedCard>
      )}

      {payload.report.recommendations?.length > 0 && (
        <DelayedCard delay={320}>
          <RecommendationCards payload={payload} />
        </DelayedCard>
      )}

      {/* SQL viewer — collapsed by default */}
      {payload.debug?.generated_code && (
        <DelayedCard delay={400}>
          <SQLViewer payload={payload} />
        </DelayedCard>
      )}

      {/* Debug panel — collapsed by default */}
      {payload.debug && (
        <DelayedCard delay={440}>
          <DebugPanel payload={payload} />
        </DelayedCard>
      )}

      {/* Per-report action bar */}
      <DelayedCard delay={500}>
        <ReportActions payload={payload} />
      </DelayedCard>
    </div>
  );
}