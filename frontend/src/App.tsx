import React, { useState, useEffect } from 'react';
import { Database } from 'lucide-react';
import MetricsDashboard from './components/MetricsDashboard';

// Import design system components
import { UploadZone, Card } from './design-system';

// Import shell layout components
import { TopNav } from './shell/TopNav';
import { LeftSidebar } from './shell/LeftSidebar';
import { RightSidebar } from './shell/RightSidebar';
import { ChatWorkspace } from './shell/ChatWorkspace';

import './App.css';

interface Column {
  name: string;
  dtype: string;
}

interface UploadResponse {
  session_id: string;
  dataset_id: string;
  row_count: number;
  columns: Column[];
}

// ── Structured report types (mirror backend schemas.py) ──────────────────────
interface ExecutiveSummary {
  headline:   string;
  summary:    string;
  confidence: 'High' | 'Medium' | 'Low';
}

interface TableResult {
  title:   string;
  columns: string[];
  rows:    any[][];
}

interface ChartSpec {
  title:       string;
  type:        string;
  plotly_json: any;
}

interface Insight        { title: string; body: string; }
interface Recommendation { title: string; body: string; }

interface ReportSection {
  title:             string;
  executive_summary: ExecutiveSummary;
  tables:            TableResult[];
  charts:            ChartSpec[];
  insights:          Insight[];
  recommendations:   Recommendation[];
}

interface DebugInfo {
  generated_sql:  string | null;
  execution_plan: string | null;
  llm_reasoning:  string | null;
}

interface DatasetInfo {
  name:    string;
  rows:    number;
  columns: number;
}

interface QueryInfo {
  question:          string;
  execution_time_ms: number;
  execution_id:      number | null;
  provider:          string;
  model:             string;
  retry_count:       number;
}

interface AnalysisResponse {
  success: boolean;
  dataset: DatasetInfo;
  query:   QueryInfo;
  report:  ReportSection;
  debug:   DebugInfo;
}

// ── Chat message (single source of truth — no duplicate chartJson / tableData) ─
interface ChatMessage {
  id:            string;
  role:          'user' | 'assistant';
  // user messages use content; assistant messages use report
  content?:      string;
  report?:       ReportSection;
  debug?:        DebugInfo;
  success?:      boolean;
  executionId?:  number | null;
  executionTime?: number;
  retryCount?:   number;
  model?:        string;
  provider?:     string;
}

export const App: React.FC = () => {
  // Navigation & UI States
  const [activeTab, setActiveTab] = useState<'analysis' | 'metrics'>('analysis');
  const [isDark, setIsDark] = useState(true);
  const [isLeftSidebarCollapsed, setIsLeftSidebarCollapsed] = useState(false);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(false);

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
    } catch (err: any) {
      setUploadError(err.message || 'Error uploading file.');
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
  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session || !question.trim() || isAnalyzing) return;

    const userQuestion = question.trim();
    const startTime    = Date.now();
    setQuestion('');
    setIsAnalyzing(true);
    setIsRightSidebarOpen(true);
    setTraceHistory([]);

    // Optimistic user bubble
    setChatHistory(prev => [...prev, {
      id:      Math.random().toString(),
      role:    'user',
      content: userQuestion,
    }]);

    // Live trace polling during execution
    const pollInterval = setInterval(() => pollTrace(session.session_id), 1500);

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ session_id: session.session_id, question: userQuestion }),
      });

      if (!response.ok) throw new Error('Analysis run failed.');

      // Backend returns a fully structured AnalysisResponse — no parsing needed
      const data: AnalysisResponse = await response.json();
      const durationMs = Date.now() - startTime;

      clearInterval(pollInterval);
      await pollTrace(session.session_id); // final trace snapshot

      setChatHistory(prev => [...prev, {
        id:            Math.random().toString(),
        role:          'assistant',
        report:        data.report,
        debug:         data.debug,
        success:       data.success,
        executionId:   data.query.execution_id,
        executionTime: durationMs,
        retryCount:    data.query.retry_count,
        model:         data.query.model,
        provider:      data.query.provider,
      }]);

      fetchSessionHistory(session.session_id);

    } catch (err: any) {
      clearInterval(pollInterval);
      // Error fallback — minimal report shape so ReportCard never crashes
      const errorReport: ReportSection = {
        title: 'Analysis Error',
        executive_summary: {
          headline:   'An error occurred while running the analysis.',
          summary:    err.message || 'Unknown error. Please check the console and try again.',
          confidence: 'Low',
        },
        tables:          [],
        charts:          [],
        insights:        [],
        recommendations: [],
      };
      setChatHistory(prev => [...prev, {
        id:      Math.random().toString(),
        role:    'assistant',
        report:  errorReport,
        success: false,
      }]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reconstruct a ChatMessage from a legacy history row (DB columns)
  const selectHistoryReport = (historyRow: any) => {
    // Rebuild a minimal report from the stored narrative + chart JSON
    const historicalReport: ReportSection = {
      title: historyRow.question,
      executive_summary: {
        headline:   historyRow.question,
        summary:    historyRow.narrative_summary || '',
        confidence: historyRow.success ? 'High' : 'Low',
      },
      tables: [],
      charts: historyRow.chart_plotly_json
        ? [{ title: 'Chart', type: 'other', plotly_json: historyRow.chart_plotly_json }]
        : [],
      insights:        [],
      recommendations: [],
    };

    setChatHistory([
      { id: 'usr-hist', role: 'user',      content: historyRow.question },
      {
        id:            'ast-hist',
        role:          'assistant',
        report:        historicalReport,
        success:       historyRow.success,
        executionId:   historyRow.id,
        executionTime: historyRow.execution_time_ms,
        retryCount:    0,
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

  // Construct history items for LeftSidebar
  const sidebarHistory = sessionQueries.map(q => ({
    id: q.id,
    question: q.question,
    success: q.success,
    duration: q.execution_time_ms,
    ts: new Date(q.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }));

  // Construct trace steps for RightSidebar
  const sidebarTrace = traceHistory.map(t => {
    const nodeName = t.metadata?.source || '';
    let status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' = 'success';
    
    // Determine status from writes or output values
    if (t.values?.validation_passed === false) {
      status = 'failed';
    } else if (t.next_node?.length > 0 && isAnalyzing) {
      status = 'running';
    }
    
    return {
      node: nodeName,
      status: status,
      duration_ms: t.metadata?.writes?.duration_ms || 250,
      details: t.values?.retry_target ? `Routing: ${t.values.retry_target}` : undefined
    };
  });

  const latestAssistantMsg = [...chatHistory].reverse().find(m => m.role === 'assistant');
  // Derive sidebar metadata from the typed report — no separate fields needed
  const latestReport  = latestAssistantMsg?.report;
  const latestDebug   = latestAssistantMsg?.debug;
  const latestRowCount = latestReport?.tables?.[0]?.rows?.length;

  return (
    <div className="flex flex-col h-screen w-screen bg-[#08080E] text-[#F4F4F8] overflow-hidden pt-[58px]">
      {/* Top Navigation */}
      <TopNav
        activeView={activeTab === 'analysis' ? 'workspace' : 'analytics'}
        onViewChange={(view) => setActiveTab(view === 'workspace' ? 'analysis' : 'metrics')}
        isDark={isDark}
        onThemeToggle={() => setIsDark(!isDark)}
      />

      {/* Main Container Layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Sidebar */}
        <LeftSidebar
          hasDataset={!!session}
          datasetName={session?.dataset_id}
          rowCount={session?.row_count}
          columns={session?.columns}
          history={sidebarHistory}
          onUpload={() => {
            // Re-use hidden input trigger or overlay
            const fileInput = document.getElementById('csv-file-hidden') as HTMLInputElement;
            fileInput?.click();
          }}
          onSelectHistory={(id) => {
            const report = sessionQueries.find(q => q.id === id);
            if (report) selectHistoryReport(report);
          }}
          selectedHistoryId={chatHistory[0]?.executionId?.toString()}
          isCollapsed={isLeftSidebarCollapsed}
          onToggleCollapse={() => setIsLeftSidebarCollapsed(!isLeftSidebarCollapsed)}
        />

        {/* Center Main Workspace */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#08080E] overflow-hidden">
          <input
            type="file"
            accept=".csv"
            id="csv-file-hidden"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileUpload(file);
            }}
          />

          {/* Dataset Info Bar */}
          {session && activeTab === 'analysis' && (
            <div className="dataset-info-bar">
              <div className="flex items-center gap-2">
                <Database size={12} className="text-violet-400" />
                <span className="font-semibold text-[#F4F4F8] text-[12px]">{session.dataset_id}</span>
                <div className="w-1 h-1 rounded-full bg-white/[0.10] mx-1" />
                <span className="text-[#6B6B80] font-medium">{session.row_count.toLocaleString()} rows</span>
                <div className="w-1 h-1 rounded-full bg-white/[0.10] mx-1" />
                <span className="text-[#6B6B80] font-medium">{session.columns.length} columns</span>
              </div>
              <div className="flex items-center gap-2 ml-auto">
                <span className="badge badge-success text-[10px]">
                  <span className="w-1 h-1 rounded-full bg-emerald-500" />
                  DuckDB · In-Memory
                </span>
              </div>
            </div>
          )}

          {activeTab === 'metrics' ? (
            <div className="flex-1 overflow-y-auto">
              <MetricsDashboard sessionQueries={sessionQueries} sessionId={session?.session_id} />
            </div>
          ) : !session ? (
            /* Upload Screen — premium centered layout */
            <div className="flex-1 overflow-y-auto px-8 py-12 flex flex-col items-center justify-center min-h-0 bg-[#08080E]">
              <div className="max-w-[480px] w-full space-y-6 animate-scale-in">
                <div className="text-center space-y-2">
                  <h1 className="text-[24px] font-bold tracking-tight text-white">
                    Autonomous Data Analyst
                  </h1>
                  <p className="text-[13px] text-[#6B6B80] max-w-sm mx-auto leading-relaxed">
                    Upload a CSV and ask questions in plain English. The AI agent queries, visualizes, and explains your data instantly.
                  </p>
                </div>

                <Card className="p-6 border-white/[0.07] bg-[#12121A] shadow-lg">
                  <UploadZone
                    onFileSelect={handleFileUpload}
                    loading={isUploading}
                    accept=".csv"
                  />
                  {uploadError && (
                    <div className="text-[12px] font-medium text-[#EF4444] bg-[#EF4444]/10 border border-[#EF4444]/15 rounded-xl p-3 mt-4 text-center animate-fade-in">
                      {uploadError}
                    </div>
                  )}
                </Card>

                <div className="flex flex-wrap items-center justify-center gap-2">
                  {['DuckDB In-Memory', 'Auto SQL', 'Plotly Charts', 'PDF Reports', 'Multi-Agent'].map(f => (
                    <span key={f} className="badge badge-neutral text-[10.5px]">{f}</span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Chat Interface Workspace Panel */
            <ChatWorkspace
              messages={chatHistory}
              question={question}
              isAnalyzing={isAnalyzing}
              onQuestionChange={setQuestion}
              onSubmit={handleAnalyze}
              hasDataset={!!session}
            />
          )}
        </main>

        {/* Right Sidebar */}
        <RightSidebar
          trace={sidebarTrace}
          isAnalyzing={isAnalyzing}
          recentActivity={sessionQueries.map(q => ({
            id: q.id,
            question: q.question,
            ts: new Date(q.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            success: q.success,
            model: 'Llama 3'
          }))}
          sessionId={session?.session_id}
          isOpen={isRightSidebarOpen}
          onToggleOpen={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
          activeExecutionTime={latestAssistantMsg?.executionTime}
          activeRetryCount={latestAssistantMsg?.retryCount}
          activeRowCount={latestRowCount}
          activeStatus={latestAssistantMsg?.success}
          activeModel={latestAssistantMsg?.model}
        />
      </div>
    </div>
  );
};

export default App;
