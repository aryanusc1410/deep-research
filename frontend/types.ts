/**
 * TypeScript type definitions for the Deep Research Agent frontend.
 * 
 * This module contains all shared type definitions used throughout
 * the application for type safety and better IDE support.
 */

import { Phase, Provider, Template, MessageRole } from "./constants";

// Re-export types from constants for convenience
export type { Phase, Provider, Template, MessageRole };

/**
 * Message in conversation history
 */
export interface Message {
  /** Role of the message sender */
  role: MessageRole;
  
  /** Message content */
  content: string;
  
  /** Optional research report (for assistant messages) */
  report?: Report;
  
  /** Optional search plan (for assistant messages) */
  plan?: string;
  
  /** Optional sources (for assistant messages) */
  sources?: Source[];
  
  /** Whether this message triggered research */
  isResearch?: boolean;
}

/**
 * Source/citation in a report
 */
export interface Source {
  /** Unique source identifier */
  id: number;
  
  /** Source title */
  title: string;
  
  /** Source URL */
  url: string;
  
  /** Short snippet/preview */
  snippet: string;
  
  /** Search query that found this source */
  query?: string;
  
  /** Which search tool found this source */
  source?: string;
}

/**
 * Research report
 */
export interface Report {
  /** Report template/structure used */
  structure: Template;
  
  /** Report content (markdown formatted) */
  content: string;
  
  /** List of cited sources */
  citations: Source[];
  
  /** Whether dual search was used */
  dual_search?: boolean;
  
  /** If dual search, which tool won */
  winning_tool?: string;
}

/**
 * Configuration for a research run
 */
export interface ResearchConfig {
  /** LLM provider to use */
  provider: Provider;
  
  /** Optional specific model ID */
  model?: string;
  
  /** Report template to generate */
  template: Template;
  
  /** Number of search queries to execute */
  search_budget: number;
}

/**
 * Request payload for research endpoint
 */
export interface ResearchRequest {
  /** Research query */
  query: string;
  
  /** Configuration options */
  config: ResearchConfig;
  
  /** Previous conversation messages */
  messages: Array<{ role: MessageRole; content: string }>;
}

/**
 * Server-Sent Event data structures
 */
export interface SSEStatusData {
  phase: Phase;
}

export interface SSELogData {
  msg: string;
}

export interface SSEProgressData {
  percent: number;
}

export interface SSEPlanData {
  text: string;
}

export interface SSESourcesData {
  count: number;
  top: Source[];
}

export interface SSEDoneData {
  report: Report;
}

export interface SSEErrorData {
  message: string;
}

/**
 * Chat response
 */
export interface ChatResponse {
  /** Assistant's response */
  response: string;
  
  /** Mode used (always "chat") */
  mode: "chat";
  
  /** Actual provider used (may differ due to fallback) */
  actual_provider: Provider;
}

/**
 * Health check response
 */
export interface HealthResponse {
  /** Service status */
  status: string;
  
  /** Service name */
  service: string;
  
  /** Service version */
  version: string;
  
  /** Available features */
  features: {
    openai: boolean;
    gemini: boolean;
    tavily: boolean;
    serpapi: boolean;
    dual_search: boolean;
  };
}

/**
 * Component prop types
 */
export interface ReportProps {
  /** Report data to display */
  report: Report;
}

export interface LogProps {
  /** Log lines to display */
  lines: string[];
}

export interface FormattedTextProps {
  /** Text content to format and display */
  content: string;
}