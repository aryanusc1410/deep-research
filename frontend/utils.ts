/**
 * Utility functions for the Deep Research Agent frontend.
 * 
 * This module contains helper functions used throughout the application
 * for common tasks like API calls, formatting, and data processing.
 */

import { API_CONFIG } from "./constants";
import type { 
  ResearchRequest, 
  ChatResponse, 
  HealthResponse,
  ResearchConfig,
  MessageRole 
} from "./types";

/**
 * API Client utilities
 */
export class APIClient {
  /**
   * Get the full URL for an API endpoint
   */
  static getEndpointURL(endpoint: string): string {
    return `${API_CONFIG.BACKEND_URL}${endpoint}`;
  }

  /**
   * Send a chat message (no research)
   */
  static async sendChatMessage(
    query: string,
    config: ResearchConfig,
    messages: Array<{ role: MessageRole; content: string }>
  ): Promise<ChatResponse> {
    const response = await fetch(this.getEndpointURL(API_CONFIG.ENDPOINTS.CHAT), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, config, messages }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: "Unknown error" }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Check API health
   */
  static async checkHealth(): Promise<HealthResponse> {
    const response = await fetch(this.getEndpointURL(API_CONFIG.ENDPOINTS.HEALTH));
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Start a research stream (returns the Response for SSE processing)
   */
  static async startResearchStream(request: ResearchRequest): Promise<Response> {
    const response = await fetch(this.getEndpointURL(API_CONFIG.ENDPOINTS.RUN), {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error("No response body");
    }

    return response;
  }
}

/**
 * Server-Sent Events (SSE) utilities
 */
export class SSEParser {
  /**
   * Parse an SSE message block into event and data
   */
  static parseBlock(block: string): { event: string; data: any } | null {
    if (!block.trim()) return null;

    let eventName = "message";
    const dataLines: string[] = [];

    for (const line of block.split(/\n/)) {
      const trimmed = line.trim();
      if (trimmed.startsWith("event:")) {
        eventName = trimmed.slice(6).trim();
      }
      if (trimmed.startsWith("data:")) {
        dataLines.push(trimmed.slice(5).trim());
      }
    }

    if (!dataLines.length) return null;

    try {
      const data = JSON.parse(dataLines.join("\n"));
      return { event: eventName, data };
    } catch {
      return null;
    }
  }

  /**
   * Process SSE stream with callback for each event
   */
  static async processStream(
    response: Response,
    onEvent: (event: string, data: any) => void,
    onError?: (error: Error) => void
  ): Promise<void> {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\n\n/);
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const parsed = this.parseBlock(block);
          if (parsed) {
            onEvent(parsed.event, parsed.data);
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error instanceof Error ? error : new Error(String(error)));
      } else {
        throw error;
      }
    }
  }
}

/**
 * Text formatting utilities
 */
export class TextFormatter {
  /**
   * Truncate text to a maximum length
   */
  static truncate(text: string, maxLength: number, suffix: string = "..."): string {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - suffix.length) + suffix;
  }

  /**
   * Extract domain from URL
   */
  static extractDomain(url: string): string {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace(/^www\./, "");
    } catch {
      return url;
    }
  }

  /**
   * Format timestamp to readable string
   */
  static formatTimestamp(date: Date = new Date()): string {
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  /**
   * Pluralize a word based on count
   */
  static pluralize(count: number, singular: string, plural?: string): string {
    if (count === 1) return singular;
    return plural || `${singular}s`;
  }
}

/**
 * Local storage utilities (with error handling)
 */
export class StorageManager {
  /**
   * Safely get item from localStorage
   */
  static getItem<T>(key: string, defaultValue: T): T {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  }

  /**
   * Safely set item in localStorage
   */
  static setItem<T>(key: string, value: T): boolean {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Safely remove item from localStorage
   */
  static removeItem(key: string): boolean {
    try {
      localStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  }
}

/**
 * Keyboard utilities
 */
export class KeyboardUtils {
  /**
   * Check if Enter was pressed without modifiers
   */
  static isEnter(event: React.KeyboardEvent): boolean {
    return (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.metaKey &&
      !event.ctrlKey
    );
  }

  /**
   * Check if Shift+Enter was pressed
   */
  static isShiftEnter(event: React.KeyboardEvent): boolean {
    return event.key === "Enter" && event.shiftKey;
  }
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Async timeout utility
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Safe JSON parse with fallback
 */
export function safeJSONParse<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json);
  } catch {
    return fallback;
  }
}