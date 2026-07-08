import { useState, useEffect, useCallback } from 'react';
import type { MetricDay } from '../types/index';
import { fetchMetrics, computeMetrics } from '../services/analytics';
import type { ComputedMetrics } from '../services/analytics';

interface UseAnalyticsResult {
  metrics: MetricDay[];
  computed: ComputedMetrics | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const useAnalytics = (): UseAnalyticsResult => {
  const [metrics, setMetrics] = useState<MetricDay[]>([]);
  const [computed, setComputed] = useState<ComputedMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMetrics();
      setMetrics(data);
      setComputed(computeMetrics(data));
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while fetching metrics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    metrics,
    computed,
    loading,
    error,
    refresh: loadData
  };
};
