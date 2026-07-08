import React, { useRef, useEffect, useState } from 'react';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { RightSidebar } from '@/components/layout/RightSidebar';
import { Report } from '@/components/report/Report';
import { UserMessage } from '@/components/chat/UserMessage';
import { ChatComposer } from '@/components/chat/ChatComposer';
import { Toaster } from '@/components/ui/Toaster';
import { Sparkles, Loader2, PanelLeftOpen } from 'lucide-react';
import { UploadZone } from '@/components/ui/UploadZone';
import { Analytics } from './Analytics';
import type { ChatMessage } from '@/types/index';

interface WorkspaceProps {
  session: any;
  hasDataset: boolean;
  datasetName?: string;
  rowCount: number;
  columns: any[];
  isUploading: boolean;
  uploadError: string | null;
  handleFileUpload: (file: File) => void;
  onUploadClick: () => void;
  history: any[];
  onSelectHistory: (id: string) => void;
  selectedHistoryId?: string;
  isLeftSidebarCollapsed: boolean;
  onToggleLeftSidebar: () => void;
  isRightSidebarCollapsed: boolean;
  onToggleRightSidebar: () => void;
  sidebarTrace: any[];
  sessionQueries: any[];
  latestAssistantMsg: any;
  latestRowCount: number | undefined;
  chatHistory: ChatMessage[];
  question: string;
  isAnalyzing: boolean;
  setQuestion: (q: string) => void;
  handleAnalyze: (e: React.FormEvent, q?: string) => void;
  activeTab: 'analysis' | 'metrics';
  setActiveTab: (tab: 'analysis' | 'metrics') => void;
  isDark: boolean;
  onThemeToggle: () => void;
}

export const Workspace: React.FC<WorkspaceProps> = ({
  session, hasDataset, datasetName, rowCount, columns,
  isUploading, uploadError, handleFileUpload, onUploadClick,
  history, onSelectHistory, selectedHistoryId,
  isLeftSidebarCollapsed, onToggleLeftSidebar,
  isRightSidebarCollapsed, onToggleRightSidebar,
  sidebarTrace, sessionQueries, latestAssistantMsg,
  chatHistory, question, isAnalyzing, setQuestion, handleAnalyze,
  activeTab, setActiveTab,
  isDark: _isDark,
  onThemeToggle: _onThemeToggle,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [activePath, setActivePath] = useState('/');

  // Sync activePath ↔ activeTab
  useEffect(() => {
    if (activeTab === 'metrics' && activePath !== '/analytics') setActivePath('/analytics');
    if (activeTab === 'analysis' && activePath === '/analytics') setActivePath('/');
  }, [activeTab]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (chatHistory.length > 0 || isAnalyzing) {
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [chatHistory, isAnalyzing]);

  const handleSetActivePath = (path: string) => {
    setActivePath(path);
    if (path === '/analytics') setActiveTab('metrics');
    else setActiveTab('analysis');
  };

  const handleSubmitQuestion = (text: string) => {
    setQuestion(text);
    setTimeout(() => {
      handleAnalyze({ preventDefault: () => {} } as React.FormEvent, text);
    }, 0);
  };

  const latestModel = latestAssistantMsg?.model;
  const latestProvider = latestAssistantMsg?.provider;

  const sidebarProps = {
    hasDataset,
    datasetName,
    rowCount,
    columns,
    history,
    onUpload: onUploadClick,
    onSelectHistory,
    selectedHistoryId,
    activePath,
    setActivePath: handleSetActivePath,
    isCollapsed: isLeftSidebarCollapsed,
    onToggleCollapse: onToggleLeftSidebar,
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Toast portal */}
      <Toaster />

      {/* Left Sidebar */}
      <AppSidebar {...sidebarProps} />

      {/* Re-open tab when sidebar is collapsed */}
      {isLeftSidebarCollapsed && (
        <button
          onClick={onToggleLeftSidebar}
          className="fixed left-0 top-1/2 z-30 -translate-y-1/2 grid h-10 w-6 place-items-center rounded-r-lg border border-l-0 border-border bg-sidebar/80 text-muted-foreground hover:bg-sidebar hover:text-foreground transition-colors"
          aria-label="Open sidebar"
        >
          <PanelLeftOpen className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Main content */}
      <main className="flex min-w-0 flex-1 flex-col h-screen overflow-hidden relative">

        {/* ── Analytics ── */}
        {activePath === '/analytics' && (
          <div className="flex-1 overflow-y-auto">
            <Analytics sessionQueries={sessionQueries} sessionId={session?.session_id} />
          </div>
        )}

        {/* ── Workspace / Chat ── */}
        {activePath === '/' && (
          <>
            {/* Top bar */}
            {hasDataset && (
              <div className="shrink-0 sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/80 px-6 py-3 backdrop-blur-xl">
                <div className="min-w-0">
                  <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    {datasetName || 'dataset.csv'} · {rowCount.toLocaleString()} rows
                  </div>
                  <h1 className="truncate text-sm font-semibold sm:text-base">
                    {chatHistory.some(m => m.role === 'assistant')
                      ? chatHistory.filter(m => m.role === 'assistant').slice(-1)[0]?.report?.title || 'Data Analysis'
                      : 'Ready for questions'}
                  </h1>
                </div>
                <div className="hidden items-center gap-2 sm:flex">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary/60 px-2.5 py-1 text-[11px] text-muted-foreground">
                    <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" /> Live
                  </span>
                  {latestModel && (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
                      <Sparkles className="h-3 w-3" /> {latestModel}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Chat / Upload area */}
            <div className="scrollbar-thin flex-1 overflow-y-auto">
              {!hasDataset ? (
                /* Upload state */
                <div className="flex h-full min-h-[calc(100vh-4rem)] flex-col items-center justify-center p-8">
                  <div className="max-w-[580px] w-full space-y-8 animate-fade-in">
                    <div className="text-center space-y-3">
                      <div className="mx-auto w-16 h-16 grid place-items-center rounded-2xl bg-[image:var(--gradient-primary)] shadow-[var(--shadow-glow)] mb-4">
                        <Sparkles className="h-8 w-8 text-primary-foreground" />
                      </div>
                      <h1 className="text-3xl font-bold tracking-tight">Autonomous Data Analyst</h1>
                      <p className="text-base text-muted-foreground max-w-md mx-auto leading-relaxed">
                        Upload a CSV and ask questions in plain English. The AI agent queries, visualizes, and explains your data instantly.
                      </p>
                    </div>
                    <UploadZone
                      onFileSelect={handleFileUpload}
                      loading={isUploading}
                      accept=".csv"
                    />
                    {uploadError && (
                      <div className="text-sm font-medium text-destructive bg-destructive/10 border border-destructive/20 rounded-xl p-4 text-center">
                        {uploadError}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Chat feed */
                <div className="mx-auto w-full max-w-4xl px-4 pt-6 pb-48">
                  {/* Empty state */}
                  {chatHistory.length === 0 && !isAnalyzing && (
                    <div className="flex flex-col items-center justify-center py-20 px-6 space-y-6 max-w-md mx-auto text-center">
                      <div className="rounded-full bg-primary/10 p-4 border border-primary/20 animate-pulse">
                        <Sparkles className="h-8 w-8 text-primary" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold tracking-tight text-foreground">Start exploring your data</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          Ask questions or click on one of the suggested prompts below to discover insights in your dataset.
                        </p>
                      </div>
                      <div className="w-full rounded-2xl border border-border bg-card/50 p-4 text-left space-y-2.5">
                        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Try asking:</div>
                        <ul className="space-y-2 text-xs font-medium text-foreground/80">
                          <li className="flex items-center gap-2 cursor-pointer hover:text-primary transition-colors" onClick={() => setQuestion("Show total revenue")}>
                            <span className="text-primary">•</span> Show total revenue
                          </li>
                          <li className="flex items-center gap-2 cursor-pointer hover:text-primary transition-colors" onClick={() => setQuestion("Top customers")}>
                            <span className="text-primary">•</span> Top customers
                          </li>
                          <li className="flex items-center gap-2 cursor-pointer hover:text-primary transition-colors" onClick={() => setQuestion("Monthly sales trend")}>
                            <span className="text-primary">•</span> Monthly sales trend
                          </li>
                          <li className="flex items-center gap-2 cursor-pointer hover:text-primary transition-colors" onClick={() => setQuestion("Revenue by country")}>
                            <span className="text-primary">•</span> Revenue by country
                          </li>
                        </ul>
                      </div>
                    </div>
                  )}

                  {/* Messages */}
                  <div className="space-y-10">
                    {chatHistory.map((msg, i) => (
                      <div key={i} className="animate-fade-in">
                        {msg.role === 'user' && <UserMessage text={msg.content || ''} />}
                        {msg.role === 'assistant' && msg.report && (
                          <div className="mt-6">
                            <Report payload={{ report: msg.report, debug: msg.debug }} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Analyzing state */}
                  {isAnalyzing && (
                    <div className="mt-8 space-y-6 animate-fade-in">
                      {question && <UserMessage text={question} />}
                      <div className="flex items-center gap-4 glass-card rounded-2xl p-5 text-muted-foreground shadow-sm border border-border/50 hover:shadow-md transition-all duration-300">
                        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-purple-500/10 text-purple-500">
                          <Loader2 className="h-5 w-5 animate-spin" />
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-foreground">Agent is analyzing...</div>
                          <div className="text-xs text-muted-foreground mt-0.5 animate-pulse">
                            {sidebarTrace.find(t => t.status === "running")?.step 
                              ? (sidebarTrace.find(t => t.status === "running")?.step === "Understanding dataset" ? "Understanding your dataset..." :
                                 sidebarTrace.find(t => t.status === "running")?.step === "Planning analysis" ? "Planning the analysis..." :
                                 sidebarTrace.find(t => t.status === "running")?.step === "Generating SQL" ? "Generating SQL..." :
                                 sidebarTrace.find(t => t.status === "running")?.step === "Executing query" ? "Executing query..." :
                                 sidebarTrace.find(t => t.status === "running")?.step === "Validating results" ? "Validating results..." :
                                 sidebarTrace.find(t => t.status === "running")?.step === "Generating report" ? "Preparing report..." : "Analyzing...")
                              : "Preparing analysis..."}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef} />
                </div>
              )}
            </div>

            {/* Composer */}
            {hasDataset && (
              <div className="shrink-0 sticky bottom-0 z-20 border-t border-border bg-background/80 px-4 py-3 backdrop-blur-xl sm:px-6">
                <div className="mx-auto max-w-4xl">
                  <ChatComposer
                    onSubmit={handleSubmitQuestion}
                    disabled={isAnalyzing}
                    model={latestModel}
                  />
                  <div className="mt-2 text-center text-[10px] text-muted-foreground">
                    DataAgent Pro can make mistakes. Always verify critical decisions.
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Right sidebar (workspace only) */}
      {hasDataset && activePath === '/' && (
        <RightSidebar
          trace={sidebarTrace}
          activeExecutionTime={latestAssistantMsg?.executionTime}
          activeRetryCount={latestAssistantMsg?.retryCount}
          activeModel={latestModel}
          activeProvider={latestProvider}
          activeStatus={latestAssistantMsg?.success}
          isCollapsed={isRightSidebarCollapsed}
          onToggleCollapse={onToggleRightSidebar}
          isAnalyzing={isAnalyzing}
          onSuggestedQuestion={handleSubmitQuestion}
          lastQuestion={[...chatHistory].reverse().find(m => m.role === 'user')?.content || ""}
          latestReport={latestAssistantMsg?.report}
        />
      )}
    </div>
  );
};
