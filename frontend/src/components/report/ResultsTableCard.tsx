import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from "lucide-react";
import { ReportCard } from "./ReportCard";
import type { AppReportPayload } from "./Report";
import { cn } from "@/lib/utils";

const DEFAULT_PAGE_SIZE = 10;

type SortDir = "asc" | "desc" | null;

function formatValue(value: any, columnName: string): { formatted: string; align: "left" | "center" | "right" } {
  if (value === null || value === undefined || value === "") {
    return { formatted: "", align: "left" };
  }

  const strVal = String(value).trim();
  const num = Number(strVal);
  
  if (isNaN(num)) {
    return { formatted: strVal, align: "left" };
  }

  const colLower = columnName.toLowerCase();
  let align: "left" | "center" | "right" = "right";

  // Center column for IDs, years, dates
  if (colLower.includes("id") || colLower === "year" || colLower === "month" || colLower === "day" || colLower === "date") {
    align = "center";
    return { formatted: strVal, align };
  }

  // Currency
  if (colLower.includes("price") || colLower.includes("revenue") || colLower.includes("sales") || colLower.includes("amount") || colLower.includes("cost") || colLower.includes("fee") || colLower.includes("profit") || colLower.includes("value")) {
    const formatted = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
    return { formatted, align };
  }

  // Percentages
  if (colLower.includes("pct") || colLower.includes("percent") || colLower.includes("margin") || colLower.includes("rate") || colLower.includes("share")) {
    const pctVal = num > 1 ? num : num * 100;
    const formatted = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(pctVal) + "%";
    return { formatted, align };
  }

  // Integers
  if (Number.isInteger(num)) {
    const formatted = new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 0
    }).format(num);
    return { formatted, align };
  }

  // General floats
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
  return { formatted, align };
}

export function ResultsTableCard({ payload, onDownloadTriggered }: { payload: AppReportPayload; onDownloadTriggered?: () => void }) {
  const table = payload.report.tables[0];
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  // Filter
  const filtered = useMemo(
    () =>
      table.rows.filter((row) =>
        row.some((v) => String(v).toLowerCase().includes(q.toLowerCase()))
      ),
    [q, table.rows]
  );

  // Sort
  const sorted = useMemo(() => {
    if (sortCol === null || sortDir === null) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sortCol];
      const bv = b[sortCol];
      const an = Number(av);
      const bn = Number(bv);
      let cmp = 0;
      if (!isNaN(an) && !isNaN(bn)) {
        cmp = an - bn;
      } else {
        cmp = String(av).localeCompare(String(bv));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortCol, sortDir]);

  const needsPagination = sorted.length > DEFAULT_PAGE_SIZE;
  const pageSize = needsPagination ? DEFAULT_PAGE_SIZE : sorted.length;
  const pageRows = sorted.slice(page * pageSize, page * pageSize + pageSize);
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));

  const handleSort = (colIdx: number) => {
    if (sortCol === colIdx) {
      setSortDir((d) => (d === "asc" ? "desc" : d === "desc" ? null : "asc"));
      if (sortDir === "desc") setSortCol(null);
    } else {
      setSortCol(colIdx);
      setSortDir("asc");
    }
    setPage(0);
  };

  const handleCSVExport = () => {
    const headers = table.columns.join(",");
    const rows = sorted.map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
    );
    const csv = [headers, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${table.title || "results"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    if (onDownloadTriggered) {
      onDownloadTriggered();
    }
  };

  const getColumnAlignment = (colIdx: number, columnName: string): "left" | "center" | "right" => {
    if (table.rows.length > 0) {
      const sampleCell = table.rows[0][colIdx];
      const { align } = formatValue(sampleCell, columnName);
      return align;
    }
    return "left";
  };

  const SortIcon = ({ colIdx }: { colIdx: number }) => {
    if (sortCol !== colIdx) return <ArrowUpDown className="h-3 w-3 opacity-40" />;
    if (sortDir === "asc") return <ArrowUp className="h-3 w-3 text-primary" />;
    if (sortDir === "desc") return <ArrowDown className="h-3 w-3 text-primary" />;
    return <ArrowUpDown className="h-3 w-3 opacity-40" />;
  };

  return (
    <ReportCard
      eyebrow="Results"
      title={table.title}
      action={
        <div className="flex items-center gap-2">
          <div className="relative hidden sm:block">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(0);
              }}
              placeholder="Filter rows…"
              className="w-40 rounded-lg border border-border bg-background/40 py-1.5 pl-8 pr-2.5 text-xs focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/25"
            />
          </div>
          <button
            onClick={handleCSVExport}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background/40 px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
            title="Download as CSV"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </button>
        </div>
      }
    >
      <div className="scrollbar-thin overflow-x-auto rounded-xl border border-border max-h-[400px]">
        <table className="w-full min-w-full text-left text-sm border-collapse">
          <thead className="sticky top-0 bg-secondary/95 backdrop-blur z-10 shadow-sm">
            <tr>
              {table.columns.map((c, colIdx) => {
                const align = getColumnAlignment(colIdx, c);
                const alignClass = align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";
                return (
                  <th
                    key={c}
                    onClick={() => handleSort(colIdx)}
                    className={cn(
                      "cursor-pointer select-none px-4 py-3.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors",
                      alignClass
                    )}
                  >
                    <span className={cn("inline-flex items-center gap-1.5", align === "right" ? "flex-row-reverse w-full" : align === "center" ? "justify-center w-full" : "")}>
                      {c}
                      <SortIcon colIdx={colIdx} />
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td
                  colSpan={table.columns.length}
                  className="px-4 py-8 text-center text-sm text-muted-foreground"
                >
                  No rows match your filter.
                </td>
              </tr>
            ) : (
              pageRows.map((row, i) => (
                <tr
                  key={i}
                  className="border-t border-border transition-colors hover:bg-secondary/40"
                >
                  {table.columns.map((c, colIdx) => {
                    const { formatted, align } = formatValue(row[colIdx], c);
                    const alignClass = align === "right" ? "text-right font-mono" : align === "center" ? "text-center" : "text-left";
                    return (
                      <td 
                        key={c} 
                        className={cn(
                          "px-4 py-3.5 text-[13px] text-foreground/90 border-t border-border/60",
                          alignClass
                        )}
                      >
                        {formatted}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
        <span>
          Showing {pageRows.length} of {sorted.length} row{sorted.length !== 1 ? "s" : ""}
          {q && ` (filtered from ${table.rows.length})`}
        </span>
        {needsPagination && (
          <div className="flex items-center gap-1">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="rounded-md border border-border px-2.5 py-1 transition-colors hover:border-primary/40 hover:text-foreground disabled:opacity-40"
            >
              Prev
            </button>
            <span className="px-2">
              {page + 1} / {totalPages}
            </span>
            <button
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              className="rounded-md border border-border px-2.5 py-1 transition-colors hover:border-primary/40 hover:text-foreground disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </ReportCard>
  );
}