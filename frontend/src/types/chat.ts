import type { ReportSection, DebugInfo } from './report';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content?: string;
  report?: ReportSection;
  debug?: DebugInfo;
  success?: boolean;
  executionId?: number | null;
  executionTime?: number;
  retryCount?: number;
  model?: string;
  provider?: string;
}
