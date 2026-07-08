import { Download } from "lucide-react";
import Plotly from "plotly.js-dist-min";
import { ReportCard } from "./ReportCard";
import PlotlyChart from "../PlotlyChart";
import type { ChartSpec } from "../../types/index";

export function ChartCard({ chart, chartId }: { chart: ChartSpec; chartId: string }) {
  const handleExport = () => {
    const el = document.getElementById(chartId);
    if (el) Plotly.downloadImage(el as any, { format: 'png', filename: chartId });
  };

  return (
    <ReportCard
      eyebrow="Chart"
      title={chart.title}
      action={
        <button 
          onClick={handleExport}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background/40 px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground cursor-pointer"
        >
          <Download className="h-3.5 w-3.5" /> PNG
        </button>
      }
    >
      <div className="h-[320px] w-full mt-4 rounded-xl overflow-hidden border border-border bg-background/20 relative z-0">
        <PlotlyChart chartData={chart.plotly_json} chartId={chartId} />
      </div>
    </ReportCard>
  );
}