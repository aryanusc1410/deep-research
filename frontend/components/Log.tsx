/**
 * Log Component
 * 
 * Displays execution logs in a terminal-style scrollable container.
 * Used for showing real-time progress updates during research operations.
 */

import React from "react";
import type { LogProps } from "../types";

/**
 * Log component for displaying execution logs
 * 
 * Features:
 * - Terminal-style appearance
 * - Scrollable container
 * - Monospace font for readability
 * - Auto-scroll to latest log (optional)
 * 
 * @param props - Component props
 * @returns Log display component
 */
export default function Log({ lines }: LogProps) {
  return (
    <div
      style={{
        maxHeight: 220,
        overflow: "auto",
        fontFamily:
          "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
        fontSize: 13,
        background: "#0b1020",
        color: "#d9e1ff",
        padding: "10px 12px",
        borderRadius: 8,
        border: "1px solid #233",
      }}
    >
      {lines.length === 0 ? (
        <div style={{ opacity: 0.7 }}>Logs will appear here…</div>
      ) : (
        lines.map((line, index) => (
          <div key={index} style={{ whiteSpace: "pre-wrap" }}>
            {line}
          </div>
        ))
      )}
    </div>
  );
}