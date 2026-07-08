export interface MetricDay {
  id: number;
  execution_date: string;
  total_executions: number;
  first_try_success_count: number;
  retry_success_count: number;
  failed_count: number;
  common_failure_types: Record<string, number>;
}

export interface HistoricalReport {
  id: number;
  question: string;
  narrative_summary: string;
  success: boolean;
  execution_time_ms: number;
  created_at: string;
}
