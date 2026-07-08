export interface ExecutiveSummary {
  headline: string;
  summary: string;
  confidence: 'High' | 'Medium' | 'Low';
}

export interface TableResult {
  title: string;
  columns: string[];
  rows: any[][];
}

export interface ChartSpec {
  title: string;
  type: string;
  plotly_json: any;
}

export interface Insight { title: string; body: string; }
export interface Recommendation { title: string; body: string; }

export interface ReportSection {
  title: string;
  executive_summary: ExecutiveSummary;
  tables: TableResult[];
  charts: ChartSpec[];
  insights: Insight[];
  recommendations: Recommendation[];
}

export interface DebugInfo {
  generated_sql: string | null;
  execution_plan: string | null;
  llm_reasoning: string | null;
}
