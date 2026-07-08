import type { MetricDay } from '../types/index';

export const fetchMetrics = async (): Promise<MetricDay[]> => {
  const response = await fetch('http://localhost:8000/metrics');
  if (!response.ok) {
    throw new Error('Failed to fetch metrics data.');
  }
  const data = await response.json();
  return data.metrics || [];
};

export interface ComputedMetrics {
  totalExecutions: number;
  firstTrySuccess: number;
  retrySuccess: number;
  failed: number;
  successRate: number;
  firstTryRate: number;
  recoveryRate: number;
  failureAggregates: Record<string, number>;
}

export const computeMetrics = (metrics: MetricDay[]): ComputedMetrics => {
  const totalExecutions = metrics.reduce((acc, curr) => acc + curr.total_executions, 0);
  const firstTrySuccess = metrics.reduce((acc, curr) => acc + curr.first_try_success_count, 0);
  const retrySuccess = metrics.reduce((acc, curr) => acc + curr.retry_success_count, 0);
  const failed = metrics.reduce((acc, curr) => acc + curr.failed_count, 0);

  const successRate = totalExecutions > 0 ? ((firstTrySuccess + retrySuccess) / totalExecutions) * 100 : 0;
  const firstTryRate = totalExecutions > 0 ? (firstTrySuccess / totalExecutions) * 100 : 0;
  
  const successCount = firstTrySuccess + retrySuccess;
  const recoveryRate = successCount > 0 ? (retrySuccess / successCount) * 100 : 0;

  const failureAggregates: Record<string, number> = {};
  metrics.forEach(day => {
    if (day.common_failure_types) {
      Object.entries(day.common_failure_types).forEach(([type, count]) => {
        failureAggregates[type] = (failureAggregates[type] || 0) + (count as number);
      });
    }
  });

  return {
    totalExecutions,
    firstTrySuccess,
    retrySuccess,
    failed,
    successRate,
    firstTryRate,
    recoveryRate,
    failureAggregates
  };
};
