import { useState } from "react";
import { ChevronDown, Copy, Terminal, Check } from "lucide-react";
import type { AppReportPayload } from "./Report";
import { cn } from "@/lib/utils";

export function SQLViewer({ payload }: { payload: AppReportPayload }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (payload.debug?.generated_sql) {
      await navigator.clipboard.writeText(payload.debug.generated_sql);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="glass-card overflow-hidden rounded-2xl">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-primary/15 text-primary">
            <Terminal className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold">Executed SQL</div>
            <div className="text-[11px] text-muted-foreground">The exact query the agent ran</div>
          </div>
        </div>
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="border-t border-border animate-fade-in">
          <div className="flex items-center justify-between border-b border-border bg-background/40 px-4 py-2 text-[11px] text-muted-foreground">
            <span className="font-mono">query.sql</span>
            <button
              onClick={copy}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-[11px] hover:border-primary/40 hover:text-foreground"
            >
              {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <pre className="scrollbar-thin max-h-96 overflow-auto px-5 py-4 text-xs leading-relaxed">
            <code className="font-mono text-foreground/90">{highlight(payload.debug?.generated_sql || '')}</code>
          </pre>
        </div>
      )}
    </section>
  );
}

const KEYWORDS = /\b(WITH|SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP|BY|ORDER|LIMIT|AS|AND|OR|SUM|COUNT|AVG|DISTINCT)\b/g;

function highlight(sql: string) {
  const parts = sql.split(KEYWORDS);
  return parts.map((p, i) =>
    /^(WITH|SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP|BY|ORDER|LIMIT|AS|AND|OR|SUM|COUNT|AVG|DISTINCT)$/.test(p) ? (
      <span key={i} className="font-semibold text-primary">
        {p}
      </span>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}