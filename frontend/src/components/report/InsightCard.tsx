import { Lightbulb, TrendingUp, AlertTriangle, Globe, Zap } from "lucide-react";
import { ReportCard } from "./ReportCard";
import type { AppReportPayload } from "./Report";

const ICONS = [Lightbulb, TrendingUp, AlertTriangle, Globe, Zap];

export function InsightCards({ payload }: { payload: AppReportPayload }) {
  const insights = payload.report.insights;

  if (!insights || insights.length === 0) {
    return (
      <ReportCard eyebrow="Insights" title="Key insights">
        <div className="py-8 text-center text-sm text-muted-foreground opacity-60">
          No insights available for this analysis.
        </div>
      </ReportCard>
    );
  }

  return (
    <ReportCard eyebrow="Insights" title="Key insights">
      <div className="grid gap-3 sm:grid-cols-2">
        {insights.map((it, idx) => {
          const Icon = ICONS[idx % ICONS.length];
          return (
            <div
              key={it.title + idx}
              className="group rounded-xl border border-border bg-background/40 p-4 transition-all hover:border-primary/40 hover:bg-primary/5 hover:shadow-[0_0_16px_-4px_oklch(0.68_0.19_295/0.2)]"
            >
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary/15 text-primary transition-transform duration-200 group-hover:scale-110">
                <Icon className="h-4 w-4" />
              </div>
              <h4 className="mt-3 text-sm font-semibold leading-snug tracking-tight">{it.title}</h4>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{it.body}</p>
            </div>
          );
        })}
      </div>
    </ReportCard>
  );
}