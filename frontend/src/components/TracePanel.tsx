import React from 'react';
import { Loader2, CheckCircle2, XCircle, AlertCircle, RefreshCw } from 'lucide-react';

interface TraceStepData {
  checkpoint_id: string;
  values: {
    retry_count: number;
    validation_passed: boolean;
    retry_target: string | null;
    graceful_failure: boolean;
  };
  next_node: string[];
  metadata: {
    source: string;
    step: number;
    writes: Record<string, any>;
  };
}

interface TracePanelProps {
  trace: TraceStepData[];
  isAnalyzing: boolean;
}

export const TracePanel: React.FC<TracePanelProps> = ({ trace, isAnalyzing }) => {
  
  // Helper to check if a specific node was executed in the trace
  const getNodeStatus = (nodeName: string): 'idle' | 'running' | 'success' | 'failed' | 'retry' => {
    if (trace.length === 0) {
      return isAnalyzing && nodeName === 'schema_profiler' ? 'running' : 'idle';
    }

    // Find the latest occurrence of nodeName in the checkpoint log
    let latestOccurrence: TraceStepData | null = null;
    let isNext = false;
    
    // Check if it is the active pending node
    const lastStep = trace[0]; // history is sorted DESC (latest first)
    if (lastStep.next_node && lastStep.next_node.includes(nodeName)) {
      isNext = true;
    }

    for (const step of trace) {
      if (step.metadata.source === nodeName) {
        latestOccurrence = step;
        break;
      }
    }

    if (isNext && isAnalyzing) {
      return 'running';
    }

    if (!latestOccurrence) {
      return 'idle';
    }

    // If validator node ran, see if it passed
    if (nodeName === 'validator') {
      const passed = latestOccurrence.values?.validation_passed;
      if (passed) return 'success';
      // If failed, see if we retried or hard crashed
      return latestOccurrence.values?.graceful_failure ? 'failed' : 'retry';
    }

    // If reflection ran, check if it completed successfully
    if (nodeName === 'reflection') {
      return latestOccurrence.values?.retry_target === 'report_agent' 
        ? (latestOccurrence.values?.graceful_failure ? 'failed' : 'success')
        : 'retry';
    }

    return 'success';
  };

  const stepsList = [
    { id: 'schema_profiler', label: 'Schema Profiler', desc: 'Profiles columns and metadata' },
    { id: 'planner', label: 'SQL-First Planner', desc: 'Formulates analysis strategy' },
    { id: 'code_generator', label: 'Code Generator', desc: 'Translates plan to SQL or Python' },
    { id: 'sandbox_executor', label: 'Sandbox Executor', desc: 'Runs query inside isolated subprocess' },
    { id: 'validator', label: 'Validator', desc: 'Checks structure and semantic correctness' },
    { id: 'reflection', label: 'Reflection & Routing', desc: 'Classifies failure and schedules retries' },
    { id: 'report_agent', label: 'Report Agent', desc: 'Compiles plotly spec and PDF report' }
  ];

  // Calculate retry counts
  const lastState = trace.length > 0 ? trace[0] : null;
  const currentRetry = lastState?.values?.retry_count || 0;

  return (
    <div className="glass-panel trace-panel" style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 className="sidebar-title" style={{ margin: 0 }}>Agent Execution Trace</h3>
        {currentRetry > 0 && (
          <span style={{ 
            fontSize: '11px', 
            background: 'var(--primary-glow)', 
            border: '1px solid var(--primary)',
            color: 'var(--text-primary)', 
            padding: '2px 8px', 
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <RefreshCw size={10} /> Retry {currentRetry}/3
          </span>
        )}
      </div>

      <div className="trace-steps">
        {stepsList.map(step => {
          const status = getNodeStatus(step.id);
          
          let icon = <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)' }} />;
          let statusClass = 'idle';

          if (status === 'running') {
            icon = <Loader2 className="animate-spin" size={14} color="var(--secondary)" />;
            statusClass = 'active';
          } else if (status === 'success') {
            icon = <CheckCircle2 size={14} color="var(--success)" />;
            statusClass = 'success';
          } else if (status === 'retry') {
            icon = <AlertCircle size={14} color="var(--warning)" />;
            statusClass = 'failed';
          } else if (status === 'failed') {
            icon = <XCircle size={14} color="var(--error)" />;
            statusClass = 'failed';
          }

          return (
            <div key={step.id} className={`trace-step ${statusClass}`} style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
              <div style={{ marginTop: '2px', display: 'flex', justifyContent: 'center', width: '16px' }}>{icon}</div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: status === 'idle' ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                  {step.label}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  {step.desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default TracePanel;
