export type StreamEventType =
  | 'status'
  | 'code_generated'
  | 'code_execution'
  | 'final_result'
  | 'error';

export interface BaseStreamEvent {
  type: StreamEventType;
}

export interface StatusEvent extends BaseStreamEvent {
  type: 'status';
  stage: 'rewriting' | 'searching' | 'executing' | 'synthesizing';
  message: string;
}

export interface CodeGeneratedEvent extends BaseStreamEvent {
  type: 'code_generated';
  language: string;
  code: string;
}

export interface CodeExecutionEvent extends BaseStreamEvent {
  type: 'code_execution';
  status: 'running' | 'success' | 'failed';
  message: string;
  output?: string;
  duration_ms?: number;
}

export interface FinalResultEvent extends BaseStreamEvent {
  type: 'final_result';
  text: string;
  images: string[];
  sources: string[];
  duration_ms: number;
}

export interface ErrorEvent extends BaseStreamEvent {
  type: 'error';
  message: string;
}

export type ChatStreamEvent =
  | StatusEvent
  | CodeGeneratedEvent
  | CodeExecutionEvent
  | FinalResultEvent
  | ErrorEvent;

export interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  codeSnippet?: string;
  codeStatus?: 'running' | 'success' | 'failed';
  images?: string[];
  sources?: string[];
  durationMs?: number;
  timestamp: string;
}
