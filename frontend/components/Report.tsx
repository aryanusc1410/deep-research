/**
 * Report Component
 * 
 * Displays research reports with formatted content, citations, and metadata.
 * Supports multiple report structures (bullet summary, tables, detailed reports).
 */

import React, { useMemo } from "react";
import type { ReportProps } from "../types";
import { TEMPLATES, SEARCH_TOOL_COLORS } from "../constants";

/**
 * Parse markdown and convert to HTML
 * 
 * @param text - Raw markdown text
 * @returns HTML string
 */
function parseMarkdown(text: string): string {
  let html = text;

  // Parse tables first (detect lines with |)
  const lines = html.split("\n");
  let inTable = false;
  let tableRows: string[] = [];
  const processedLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Check if this is a table row (contains |)
    if (line.includes("|")) {
      if (!inTable) {
        inTable = true;
        tableRows = [];
      }
      tableRows.push(line);

      // Check if next line is not a table row
      if (i === lines.length - 1 || !lines[i + 1].includes("|")) {
        // End of table, process it
        const tableHtml = buildTableHtml(tableRows);
        processedLines.push(tableHtml);
        inTable = false;
        tableRows = [];
      }
    } else {
      processedLines.push(line);
    }
  }

  html = processedLines.join("\n");

  // Headers
  html = html.replace(
    /^### (.*$)/gim,
    '<h3 style="margin: 1.5rem 0 0.75rem; font-size: 1.25rem; font-weight: 600; color: #111;">$1</h3>'
  );
  html = html.replace(
    /^## (.*$)/gim,
    '<h2 style="margin: 1.75rem 0 1rem; font-size: 1.5rem; font-weight: 600; color: #111;">$1</h2>'
  );
  html = html.replace(
    /^# (.*$)/gim,
    '<h1 style="margin: 2rem 0 1rem; font-size: 1.875rem; font-weight: 700; color: #111;">$1</h1>'
  );

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Citations [1], [2], etc.
  html = html.replace(
    /\[(\d+)\]/g,
    '<sup style="color: #6366f1; font-weight: 600; cursor: pointer;" data-citation="$1">[$1]</sup>'
  );

  // Line breaks
  html = html.replace(/\n\n/g, "<br><br>");
  html = html.replace(/\n/g, "<br>");

  return html;
}

/**
 * Build HTML table from markdown table rows
 * 
 * @param rows - Array of markdown table row strings
 * @returns HTML table string
 */
function buildTableHtml(rows: string[]): string {
  if (rows.length === 0) return "";

  // Remove separator row (contains only |, -, and spaces)
  const contentRows = rows.filter((row) => !/^[\|\-\s]+$/.test(row));

  if (contentRows.length === 0) return "";

  const tableStyle =
    "width: 100%; border-collapse: collapse; margin: 1.5rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);";
  const thStyle =
    "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.75rem 1rem; text-align: left; font-weight: 600; border: 1px solid #e5e7eb;";
  const tdStyle =
    "padding: 0.75rem 1rem; border: 1px solid #e5e7eb; background: #fafafa;";

  let html = `<table style="${tableStyle}">`;

  // First row is header
  const headerCells = contentRows[0]
    .split("|")
    .map((c) => c.trim())
    .filter((c) => c);
  html += "<thead><tr>";
  headerCells.forEach((cell) => {
    html += `<th style="${thStyle}">${cell}</th>`;
  });
  html += "</tr></thead>";

  // Remaining rows are body
  if (contentRows.length > 1) {
    html += "<tbody>";
    for (let i = 1; i < contentRows.length; i++) {
      const cells = contentRows[i]
        .split("|")
        .map((c) => c.trim())
        .filter((c) => c);
      html += "<tr>";
      cells.forEach((cell) => {
        // Process citations in cells
        const processed = cell.replace(
          /\[(\d+)\]/g,
          '<sup style="color: #6366f1; font-weight: 600;">[$1]</sup>'
        );
        html += `<td style="${tdStyle}">${processed}</td>`;
      });
      html += "</tr>";
    }
    html += "</tbody>";
  }

  html += "</table>";
  return html;
}

/**
 * Report component for displaying research reports
 * 
 * @param props - Component props
 * @returns Formatted report component
 */
export default function Report({ report }: ReportProps) {
  if (!report) return null;

  const content =
    typeof report === "string"
      ? report
      : report.content ?? JSON.stringify(report, null, 2);
  const citations = Array.isArray(report.citations) ? report.citations : [];
  const isDetailed = report.structure === TEMPLATES.DETAILED_REPORT;

  const htmlContent = useMemo(() => parseMarkdown(content), [content]);

  return (
    <div
      style={{
        background: "linear-gradient(to bottom, #f8fafc, #ffffff)",
        borderRadius: "1rem",
        padding: "2rem",
        boxShadow:
          "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1.5rem",
          paddingBottom: "1rem",
          borderBottom: "2px solid #e5e7eb",
        }}
      >
        <div
          style={{
            width: "3rem",
            height: "3rem",
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            borderRadius: "0.75rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "1.5rem",
          }}
        >
          {isDetailed ? "📄" : "📊"}
        </div>
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: "1.875rem",
              fontWeight: "700",
              color: "#111",
            }}
          >
            Research Report
          </h2>
          {isDetailed && (
            <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "#6b7280" }}>
              Comprehensive analysis • {citations.length} sources
            </p>
          )}
        </div>
      </div>

      {/* Content */}
      {isDetailed ? (
        <details open>
          <summary
            style={{
              cursor: "pointer",
              padding: "1rem",
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "white",
              borderRadius: "0.75rem",
              fontWeight: "600",
              fontSize: "1.1rem",
              marginBottom: "1.5rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              listStyle: "none",
            }}
          >
            <span style={{ fontSize: "1.25rem" }}>📖</span>
            Click to expand full detailed report
            <span style={{ marginLeft: "auto", fontSize: "0.9rem" }}>▼</span>
          </summary>
          <article
            style={{
              lineHeight: 1.8,
              fontSize: "1rem",
              color: "#374151",
            }}
            dangerouslySetInnerHTML={{ __html: htmlContent }}
          />
        </details>
      ) : (
        <article
          style={{
            lineHeight: 1.8,
            fontSize: "1rem",
            color: "#374151",
          }}
          dangerouslySetInnerHTML={{ __html: htmlContent }}
        />
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div
          style={{
            marginTop: "2.5rem",
            paddingTop: "2rem",
            borderTop: "2px solid #e5e7eb",
          }}
        >
          <h3
            style={{
              fontSize: "1.25rem",
              fontWeight: "600",
              marginBottom: "1rem",
              color: "#111",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span style={{ fontSize: "1.5rem" }}>🔗</span>
            Sources & References
          </h3>
          <ol
            style={{
              paddingLeft: "1.5rem",
              margin: "0",
              display: "grid",
              gap: "0.75rem",
            }}
          >
            {citations.map((citation: any) => (
              <li
                key={citation.id || citation.url}
                style={{
                  padding: "0.75rem",
                  background: "#f9fafb",
                  borderRadius: "0.5rem",
                  borderLeft: "3px solid #6366f1",
                  transition: "all 0.2s",
                }}
              >
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: "#6366f1",
                    textDecoration: "none",
                    fontWeight: "500",
                    display: "block",
                  }}
                >
                  {citation.title || citation.url}
                </a>
                {citation.snippet && (
                  <p
                    style={{
                      margin: "0.5rem 0 0",
                      fontSize: "0.875rem",
                      color: "#6b7280",
                      lineHeight: 1.5,
                    }}
                  >
                    {citation.snippet}
                  </p>
                )}
                {citation.source && (
                  <span
                    style={{
                      display: "inline-block",
                      marginTop: "0.5rem",
                      padding: "0.25rem 0.5rem",
                      background:
                        SEARCH_TOOL_COLORS[citation.source]?.background || "#dbeafe",
                      color: SEARCH_TOOL_COLORS[citation.source]?.color || "#1e40af",
                      fontSize: "0.75rem",
                      borderRadius: "0.375rem",
                      fontWeight: "600",
                    }}
                  >
                    {citation.source}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}