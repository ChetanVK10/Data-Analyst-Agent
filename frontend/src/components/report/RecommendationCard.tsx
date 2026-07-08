import { CheckCircle2, ArrowRight } from "lucide-react";
import { ReportCard } from "./ReportCard";
import type { AppReportPayload } from "./Report";

export function RecommendationCards({ payload }: { payload: AppReportPayload }) {
  const recs = payload.report.recommendations;

  if (!recs || recs.length === 0) {
    return (
      <ReportCard eyebrow="Recommendations" title="What to do next">
        <div className="py-8 text-center text-sm text-muted-foreground opacity-60">
          No recommendations available for this analysis.
        </div>
      </ReportCard>
    );
  }

  return (
    <ReportCard eyebrow="Recommendations" title="What to do next">
      <div className="space-y-3">
        {recs.map((r, idx) => (
          <div
            key={r.title + idx}
            className="group flex items-start gap-3 rounded-xl border border-success/25 bg-success/[0.05] p-4 transition-all hover:border-success/50 hover:bg-success/[0.08]"
          >
            <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-success/20 text-success transition-transform duration-200 group-hover:scale-105">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <h4 className="text-sm font-semibold leading-snug tracking-tight">{r.title}</h4>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{r.body}</p>
            </div>
            <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground/40 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-success" />
          </div>
        ))}
      </div>
    </ReportCard>
  );
}