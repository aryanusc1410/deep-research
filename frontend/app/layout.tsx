import "../styles/globals.css";

export const metadata = {
  title: "Deep Research",
  description: "LangGraph-based research agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
