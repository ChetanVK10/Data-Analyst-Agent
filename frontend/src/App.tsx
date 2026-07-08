import React, { useState, useEffect, useRef } from 'react';
import { Workspace } from './pages/Workspace';
import { toast } from './lib/toast';

import type {
  UploadResponse,
  ReportSection,
  AnalysisResponse,
  ChatMessage
} from './types/index';

export const App: React.FC = () => {
  // Navigation & UI States
  const [activeTab, setActiveTab] = useState<'analysis' | 'metrics'>('analysis');
  const [isDark, setIsDark] = useState(true);
  const [isLeftSidebarCollapsed, setIsLeftSidebarCollapsed] = useState(false);
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = useState(false);

  // Session & Dataset State
  const [session, setSession] = useState<UploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  // Analysis State
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [traceHistory, setTraceHistory] = useState<any[]>([]);

  // Historical Session list
  const [sessionQueries, setSessionQueries] = useState<any[]>([]);

  // Hidden file input ref
  const fileInputRef = useRef<HTMLInputElement>(null);

  // CSV Drag and drop helper
  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setUploadError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed. Please ensure file is a valid CSV.');
      }

      const data: UploadResponse = await response.json();
      setSession(data);
      // Reset state on new upload
      setChatHistory([]);
      setTraceHistory([]);
      setSessionQueries([]);
      toast(`Dataset loaded — ${data.row_count?.toLocaleString() ?? 0} rows`, 'success');
    } catch (err: any) {
      setUploadError(err.message || 'Error uploading file.');
      toast(err.message || 'Upload failed', 'error');
    } finally {
      setIsUploading(false);
    }
  };

  // Poll LangGraph traces
  const pollTrace = async (sessionId: string): Promise<any[]> => {
    try {
      const response = await fetch(`http://localhost:8000/execution/${sessionId}/trace`);
      if (response.ok) {
        const data = await response.json();
        setTraceHistory(data.trace || []);
        return data.trace || [];
      }
    } catch (e) {
      console.warn("Failed to poll execution trace", e);
    }
    return [];
  };

  // Fetch session history
  const fetchSessionHistory = async (sessionId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/history/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setSessionQueries(data.history || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Analyze Query action
  const handleAnalyze = async (e: React.FormEvent, submittedQuestion?: string) => {
    e.preventDefault();
    const userQuestion = (submittedQuestion || question).trim();
    if (!session || !userQuestion || isAnalyzing) return;

    const startTime = Date.now();
    setQuestion('');
    setIsAnalyzing(true);
    setIsRightSidebarCollapsed(false);
    setTraceHistory([]);

    // Optimistic user bubble
    setChatHistory(prev => [...prev, {
      id: Math.random().toString(),
      role: 'user',
      content: userQuestion,
    }]);

    // Live trace polling during execution
    const pollInterval = setInterval(() => pollTrace(session.session_id), 1500);

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id, question: userQuestion }),
      });

      if (!response.ok) throw new Error('Analysis run failed.');

      const data: AnalysisResponse = await response.json();
      const durationMs = Date.now() - startTime;

      clearInterval(pollInterval);
      await pollTrace(session.session_id);

      setChatHistory(prev => [...prev, {
        id: Math.random().toString(),
        role: 'assistant',
        report: data.report,
        debug: data.debug,
        success: data.success,
        executionId: data.query.execution_id,
        executionTime: durationMs,
        retryCount: data.query.retry_count,
        model: data.query.model,
        provider: data.query.provider,
      }]);

      fetchSessionHistory(session.session_id);

    } catch (err: any) {
      clearInterval(pollInterval);
      const errorReport: ReportSection = {
        title: 'Analysis Error',
        executive_summary: {
          headline: 'An error occurred while running the analysis.',
          summary: err.message || 'Unknown error. Please check the console and try again.',
          confidence: 'Low',
        },
        tables: [],
        charts: [],
        insights: [],
        recommendations: [],
      };
      setChatHistory(prev => [...prev, {
        id: Math.random().toString(),
        role: 'assistant',
        report: errorReport,
        success: false,
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reconstruct a ChatMessage from a legacy history row
  const selectHistoryReport = (historyRow: any) => {
    const historicalReport: ReportSection = {
      title: historyRow.question,
      executive_summary: {
        headline: historyRow.question,
        summary: historyRow.narrative_summary || '',
        confidence: historyRow.success ? 'High' : 'Low',
      },
      tables: [],
      charts: historyRow.chart_plotly_json
        ? [{ title: 'Chart', type: 'other', plotly_json: historyRow.chart_plotly_json }]
        : [],
      insights: [],
      recommendations: [],
    };

    setChatHistory([
      { id: 'usr-hist', role: 'user', content: historyRow.question },
      {
        id: 'ast-hist',
        role: 'assistant',
        report: historicalReport,
        success: historyRow.success,
        executionId: historyRow.id,
        executionTime: historyRow.execution_time_ms,
        retryCount: 0,
      },
    ]);
  };

  // Sync dark theme class on document element
  useEffect(() => {
    const root = window.document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDark]);

  // Sidebar history items
  const sidebarHistory = sessionQueries.map(q => ({
    id: q.id,
    question: q.question,
    success: q.success,
    duration: q.execution_time_ms,
    created_at: q.created_at,
    ts: new Date(q.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }));

  // Trace steps for RightSidebar
  const sidebarTrace = traceHistory.map(t => {
    const nodeName = t.metadata?.source || '';
    let status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' = 'success';

    if (t.values?.validation_passed === false) {
      status = 'failed';
    } else if (t.next_node?.length > 0 && isAnalyzing) {
      status = 'running';
    }

    return {
      step: nodeName,
      status,
      duration_ms: t.metadata?.writes?.duration_ms || 250,
      details: t.values?.retry_target ? `Routing: ${t.values.retry_target}` : undefined
    };
  });

  const latestAssistantMsg = [...chatHistory].reverse().find(m => m.role === 'assistant');
  const latestReport = latestAssistantMsg?.report;
  const latestRowCount = latestReport?.tables?.[0]?.rows?.length;

  return (
    <div className="flex h-screen w-screen bg-background text-foreground overflow-hidden">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        id="csv-file-hidden"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileUpload(file);
          // Reset value so same file can be re-uploaded
          e.target.value = '';
        }}
      />

      <Workspace
        session={session}
        hasDataset={!!session}
        datasetName={session?.dataset_id}
        rowCount={session?.row_count || 0}
        columns={session?.columns || []}
        isUploading={isUploading}
        uploadError={uploadError}
        handleFileUpload={handleFileUpload}
        onUploadClick={() => fileInputRef.current?.click()}
        history={sidebarHistory}
        onSelectHistory={(id) => {
          const report = sessionQueries.find(q => q.id.toString() === id.toString());
          if (report) selectHistoryReport(report);
        }}
        selectedHistoryId={latestAssistantMsg?.executionId?.toString()}
        isLeftSidebarCollapsed={isLeftSidebarCollapsed}
        onToggleLeftSidebar={() => setIsLeftSidebarCollapsed(c => !c)}
        isRightSidebarCollapsed={isRightSidebarCollapsed}
        onToggleRightSidebar={() => setIsRightSidebarCollapsed(c => !c)}
        sidebarTrace={sidebarTrace}
        sessionQueries={sessionQueries}
        latestAssistantMsg={latestAssistantMsg}
        latestRowCount={latestRowCount}
        chatHistory={chatHistory}
        question={question}
        isAnalyzing={isAnalyzing}
        setQuestion={setQuestion}
        handleAnalyze={handleAnalyze}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isDark={isDark}
        onThemeToggle={() => setIsDark(d => !d)}
      />
    </div>
  );
};

export default App;
