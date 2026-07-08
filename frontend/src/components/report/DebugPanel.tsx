import { useState } from "react";
import { Bug, ChevronDown } from "lucide-react";
import type { AppReportPayload } from "./Report";
import { cn } from "@/lib/utils";

export function DebugPanel({ payload }: { payload: AppReportPayload }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="glass-card overflow-hidden rounded-2xl">
      <button onClick={() => setOpen((v) => !v)} className="flex w-full items-center justify-between px-5 py-4 text-left">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-secondary text-muted-foreground">
            <Bug className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold">Debug information</div>
            <div className="text-[11px] text-muted-foreground">Reasoning, plan, and runtime metadata</div>
          </div>
        </div>
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && payload.debug && (
        <div className="grid gap-3 border-t border-border p-5 animate-fade-in md:grid-cols-2">
          {payload.debug.llm_reasoning && <Field label="LLM reasoning" value={payload.debug.llm_reasoning} />}
          {payload.debug.execution_plan && <Field label="Execution plan" value={payload.debug.execution_plan} mono />}
        </div>
      )}
    </section>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-background/40 p-3 md:col-span-2">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn("mt-1 text-xs leading-relaxed text-foreground/90", mono && "font-mono")}>{value}</div>
    </div>
  );
}
