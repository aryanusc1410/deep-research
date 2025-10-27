/**
 * Frontend constants and configuration values.
 * 
 * This module centralizes all constant values used throughout the frontend,
 * making it easier to maintain and modify configuration settings.
 */

/**
 * API Configuration
 */
export const API_CONFIG = {
  /** Base URL for backend API (from environment or fallback to localhost) */
  BACKEND_URL: (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/$/, ""),
  
  /** API endpoints */
  ENDPOINTS: {
    RUN: "/run",
    RUN_SYNC: "/run_sync",
    CHAT: "/chat",
    HEALTH: "/health",
  },
} as const;

/**
 * Server-Sent Events (SSE) Configuration
 */
export const SSE_EVENTS = {
  STATUS: "status",
  LOG: "log",
  PROGRESS: "progress",
  PLAN: "plan",
  SOURCES: "sources",
  DONE: "done",
  ERROR: "error",
} as const;

/**
 * Research Phases
 */
export const PHASES = {
  IDLE: "",
  PLANNING: "planning",
  SEARCHING: "searching",
  SYNTHESIZING: "synthesizing",
  DONE: "done",
  ERROR: "error",
} as const;

/**
 * Message Roles
 */
export const MESSAGE_ROLES = {
  USER: "user",
  ASSISTANT: "assistant",
} as const;

/**
 * LLM Providers
 */
export const PROVIDERS = {
  OPENAI: "openai",
  GEMINI: "gemini",
} as const;

/**
 * Report Templates
 */
export const TEMPLATES = {
  BULLET_SUMMARY: "bullet_summary",
  TWO_COLUMN: "two_column",
  DETAILED_REPORT: "detailed_report",
} as const;

/**
 * Template Display Names
 */
export const TEMPLATE_LABELS = {
  [TEMPLATES.BULLET_SUMMARY]: "Bullet summary",
  [TEMPLATES.TWO_COLUMN]: "Claim/Evidence table",
  [TEMPLATES.DETAILED_REPORT]: "Detailed report (long)",
} as const;

/**
 * Provider Display Names
 */
export const PROVIDER_LABELS = {
  [PROVIDERS.OPENAI]: "OpenAI",
  [PROVIDERS.GEMINI]: "Gemini",
} as const;

/**
 * UI Configuration
 */
export const UI_CONFIG = {
  /** Search budget limits */
  SEARCH_BUDGET: {
    MIN: 1,
    MAX: 10,
    DEFAULT: 4,
  },
  
  /** Progress reset delay in milliseconds */
  PROGRESS_RESET_DELAY: 2000,
  
  /** Maximum message history to display */
  MAX_DISPLAYED_MESSAGES: 50,
  
  /** Top sources to show in preview */
  TOP_SOURCES_PREVIEW: 5,
} as const;

/**
 * Badge Styles by Phase
 */
export const PHASE_BADGE_STYLES = {
  idle: { background: "#f3f4f6", color: "#6b7280", borderColor: "#d1d5db" },
  planning: { background: "#fef3c7", color: "#92400e", borderColor: "#fcd34d" },
  searching: { background: "#dbeafe", color: "#1e40af", borderColor: "#60a5fa" },
  synthesizing: { background: "#e0e7ff", color: "#3730a3", borderColor: "#818cf8" },
  done: { background: "#d1fae5", color: "#065f46", borderColor: "#34d399" },
  error: { background: "#fee2e2", color: "#991b1b", borderColor: "#f87171" },
} as const;

/**
 * Search Tool Names
 */
export const SEARCH_TOOLS = {
  TAVILY: "Tavily",
  SERP: "SerpAPI",
} as const;

/**
 * Search Tool Colors
 */
export const SEARCH_TOOL_COLORS = {
  [SEARCH_TOOLS.TAVILY]: {
    background: "#dbeafe",
    color: "#1e40af",
  },
  [SEARCH_TOOLS.SERP]: {
    background: "#fef3c7",
    color: "#92400e",
  },
} as const;

/**
 * Type Definitions
 */
export type Phase = typeof PHASES[keyof typeof PHASES];
export type Provider = typeof PROVIDERS[keyof typeof PROVIDERS];
export type Template = typeof TEMPLATES[keyof typeof TEMPLATES];
export type MessageRole = typeof MESSAGE_ROLES[keyof typeof MESSAGE_ROLES];
export type SSEEvent = typeof SSE_EVENTS[keyof typeof SSE_EVENTS];