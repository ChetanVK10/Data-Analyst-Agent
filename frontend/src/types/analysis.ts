import type { ReportSection, DebugInfo } from './report';

export interface AnalysisResponse {
  success: boolean;
  dataset: DatasetInfo;
  query: QueryInfo;
  report: ReportSection;
  debug: DebugInfo;
}

export interface Column {
  name: string;
  dtype: string;
}

export interface UploadResponse {
  session_id: string;
  dataset_id: string;
  row_count: number;
  columns: Column[];
}

export interface DatasetInfo {
  name: string;
  rows: number;
  columns: number;
}

export interface QueryInfo {
  question: string;
  execution_time_ms: number;
  execution_id: number | null;
  provider: string;
  model: string;
  retry_count: number;
}
