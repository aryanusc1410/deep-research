/**
 * Root Layout Component
 * 
 * Provides the base HTML structure and global styling for the application.
 * This layout wraps all pages in the application.
 */

import "../styles/globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Deep Research Agent",
  description: "LangGraph-powered research assistant with real-time streaming", 
};
export const viewport: Viewport = {
  width:'device-width', 
  initialScale:1,
};

/**
 * Root layout component
 * 
 * @param children - Child components to render
 * @returns Root HTML structure
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}