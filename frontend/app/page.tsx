"use client";
import { useRef, useState } from "react";
import Report from "@/components/Report";
import Log from "@/components/Log";
import FormattedText from "@/components/FormattedText";

type Phase = "" | "planning" | "searching" | "synthesizing" | "done" | "error";

interface Message {
  role: "user" | "assistant";
  content: string;
  report?: any;
  plan?: string;
  sources?: any[];
  isResearch?: boolean;
}

export default function Page() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [phase, setPhase] = useState<Phase>("");
  const [busy, setBusy] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState<number>(0);
  const [inputValue, setInputValue] = useState("");
  const [researchMode, setResearchMode] = useState(true);
  const [showConfig, setShowConfig] = useState(false);
  
  // Config state
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("");
  const [template, setTemplate] = useState("bullet_summary");
  const [budget, setBudget] = useState(4);

  const backendBase = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

  function pushLog(line: string) {
    console.log("[Frontend Log]", line);
    setLogs(prev => [...prev, line]);
  }

  async function sendChatMessage(query: string) {
    if (!query.trim() || busy) return;

    const userMsg: Message = { role: "user", content: query, isResearch: false };
    setMessages(prev => [...prev, userMsg]);
    setInputValue("");
    setBusy(true);

    try {
      const url = `${backendBase}/chat`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          config: { provider, model, template, search_budget: budget },
          messages: messages.map(m => ({ role: m.role, content: m.content }))
        }),
      });

      const data = await res.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: data.response,
        isResearch: false
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        role: "assistant",
        content: `Error: ${err.message}`,
        isResearch: false
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setBusy(false);
    }
  }

  async function sendResearchMessage(query: string) {
    if (!query.trim() || busy) return;

    const userMsg: Message = { role: "user", content: query, isResearch: true };
    setMessages(prev => [...prev, userMsg]);
    setInputValue("");

    setBusy(true);
    setPhase("");
    setLogs([]);
    setProgress(0);

    let currentReport: any = null;
    let currentPlan = "";
    let currentSources: any[] = [];

    try {
      const url = `${backendBase}/run`;
      
      const res = await fetch(url, {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query, 
          config: { provider, model, template, search_budget: budget }, 
          messages: messages.filter(m => !m.isResearch).map(m => ({ role: m.role, content: m.content }))
        }),
        cache: "no-store",
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buf += dec.decode(value, { stream: true });
        const blocks = buf.split(/\n\n/);
        buf = blocks.pop() || "";

        for (const block of blocks) {
          if (!block.trim()) continue;
          
          let eventName = "message";
          const dataLines: string[] = [];
          
          for (const line of block.split(/\n/)) {
            const trimmed = line.trim();
            if (trimmed.startsWith("event:")) eventName = trimmed.slice(6).trim();
            if (trimmed.startsWith("data:")) dataLines.push(trimmed.slice(5).trim());
          }
          
          if (!dataLines.length) continue;

          let payload: any;
          try { payload = JSON.parse(dataLines.join("\n")); }
          catch { continue; }

          if (eventName === "status") {
            setPhase(payload.phase || "");
            pushLog(`STATUS: ${payload.phase}`);
          } else if (eventName === "plan") {
            currentPlan = payload.text || "";
            pushLog("PLAN received");
          } else if (eventName === "sources") {
            currentSources = payload.top || [];
            pushLog(`SOURCES: ${payload.count} unique`);
          } else if (eventName === "log") {
            if (payload.msg) pushLog(payload.msg);
          } else if (eventName === "progress") {
            if (typeof payload.percent === "number") setProgress(payload.percent);
          } else if (eventName === "done") {
            currentReport = payload.report ?? payload;
            setPhase("done");
            setProgress(100);
            pushLog("DONE.");
          } else if (eventName === "error") {
            setPhase("error");
            pushLog("ERROR: " + (payload.message || "unknown"));
          }
        }
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: "Research complete!",
        report: currentReport,
        plan: currentPlan,
        sources: currentSources,
        isResearch: true
      };
      setMessages(prev => [...prev, assistantMsg]);

    } catch (err: any) {
      console.error("[Frontend] Error:", err);
      setPhase("error");
      pushLog("CLIENT ERROR: " + err.message);
      
      const errorMsg: Message = {
        role: "assistant",
        content: `Error: ${err.message}`,
        isResearch: true
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setBusy(false);
      // Reset progress after a short delay when done
      setTimeout(() => {
        if (!busy) {
          setProgress(0);
          setPhase("");
        }
      }, 2000);
    }
  }

  function sendMessage(query: string) {
    if (researchMode) {
      sendResearchMessage(query);
    } else {
      sendChatMessage(query);
    }
  }

  return (
    <main>
      <h1>Deep Research</h1>

      {/* Chat Messages */}
      <div style={{ marginBottom: '1.5rem' }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{
            marginBottom: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            {msg.role === 'user' ? (
              <div style={{ width: '100%', maxWidth: '100%' }}>
                <div style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  padding: '1rem 1.25rem',
                  borderRadius: '1rem',
                  maxWidth: '70%',
                  fontSize: '1rem',
                  lineHeight: 1.6,
                  boxShadow: '0 2px 8px rgba(102, 126, 234, 0.3)',
                  marginLeft: 'auto',
                  wordWrap: 'break-word',
                  overflowWrap: 'break-word'
                }}>
                  {msg.content}
                </div>
                {msg.isResearch && (
                  <div style={{
                    fontSize: '0.75rem',
                    color: '#6b7280',
                    marginTop: '0.25rem',
                    textAlign: 'right'
                  }}>
                    🔬 Research mode
                  </div>
                )}
              </div>
            ) : (
              <div style={{ width: '100%', maxWidth: '100%' }}>
                {msg.report ? (
                  <>
                    {msg.report.dual_search && (
                      <div style={{
                        background: msg.report.winning_tool === 'SerpAPI' 
                          ? 'linear-gradient(90deg, #fef3c7, #fde68a)' 
                          : 'linear-gradient(90deg, #dbeafe, #bfdbfe)',
                        border: msg.report.winning_tool === 'SerpAPI'
                          ? '2px solid #f59e0b'
                          : '2px solid #3b82f6',
                        borderRadius: '0.75rem',
                        padding: '0.75rem 1rem',
                        marginBottom: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        color: msg.report.winning_tool === 'SerpAPI' ? '#92400e' : '#1e40af',
                        flexWrap: 'wrap'
                      }}>
                        <span style={{fontSize: '1.25rem'}}>🏆</span>
                        <span>Winner: {msg.report.winning_tool} provided the best results</span>
                      </div>
                    )}
                    <Report report={msg.report} />
                  </>
                ) : (
                  <div className="card" style={{
                    background: '#f9fafb',
                    borderColor: '#e5e7eb',
                    wordWrap: 'break-word',
                    overflowWrap: 'break-word'
                  }}>
                    <FormattedText content={msg.content} />
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input Box with Configuration, Research Toggle & Progress Bar */}
      <div className="card" style={{
        position: 'sticky',
        bottom: '1rem',
        background: 'rgba(255, 255, 255, 0.98)',
        backdropFilter: 'blur(10px)',
        boxShadow: '0 -4px 12px rgba(0, 0, 0, 0.15)',
        padding: '1.5rem'
      }}>
        {/* Progress Bar - Only shows when research is active */}
        {busy && researchMode && (
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '0.5rem'
            }}>
              <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#6b7280' }}>
                Research Progress
              </span>
              <span className={`badge ${phase}`} style={{ animation: 'none' }}>
                {phase || "starting"}
              </span>
            </div>
            <div style={{ 
              height: 8, 
              background: "#e5e7eb", 
              borderRadius: 999,
              overflow: 'hidden'
            }}>
              <div style={{
                height: "100%",
                width: `${progress}%`,
                background: "linear-gradient(90deg, #6366f1, #8b5cf6)",
                borderRadius: 999,
                transition: "width .3s ease"
              }} />
            </div>
            <div style={{
              fontSize: '0.75rem',
              color: '#9ca3af',
              marginTop: '0.25rem',
              textAlign: 'right'
            }}>
              {progress}%
            </div>
          </div>
        )}

        {/* Configuration Row - Collapsible on mobile */}
        <details open={showConfig} onToggle={(e: any) => setShowConfig(e.target.open)} style={{ marginBottom: '1rem' }}>
          <summary style={{ 
            cursor: 'pointer', 
            fontWeight: '600', 
            fontSize: '0.9rem',
            color: '#6b7280',
            marginBottom: showConfig ? '0.75rem' : '0',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            listStylePosition: 'inside',
            WebkitTapHighlightColor: 'transparent'
          }}>
            ⚙️ Configuration
          </summary>
          <div className="grid grid-4" style={{ marginTop: '0.75rem', gap: '0.5rem' }}>
            <select value={provider} onChange={e => setProvider(e.target.value)} disabled={busy}>
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
            <input 
              value={model} 
              onChange={e => setModel(e.target.value)}
              placeholder="(optional) model id" 
              disabled={busy}
            />
            <select value={template} onChange={e => setTemplate(e.target.value)} disabled={busy}>
              <option value="bullet_summary">Bullet summary</option>
              <option value="two_column">Claim/Evidence table</option>
              <option value="detailed_report">Detailed report (long)</option>
            </select>
            <input 
              type="number" 
              min={1} 
              max={10} 
              value={budget}
              onChange={e => setBudget(Number(e.target.value))}
              disabled={busy}
              style={{ width: '100%' }}
              placeholder="Search budget"
            />
          </div>
        </details>

        <form onSubmit={(e) => {
          e.preventDefault();
          sendMessage(inputValue);
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ flex: 1 }}>
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={researchMode ? "Ask a research question..." : "Chat with AI (no research)..."}
                rows={3}
                disabled={busy}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
                    e.preventDefault();
                    sendMessage(inputValue);
                  }
                }}
                style={{ width: '100%', resize: 'vertical' }}
              />
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.75rem', 
                marginTop: '0.5rem',
                fontSize: '0.875rem',
                flexWrap: 'wrap'
              }}>
                <label style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '0.5rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  color: researchMode ? '#6366f1' : '#6b7280',
                  WebkitTapHighlightColor: 'transparent'
                }}>
                  <input
                    type="checkbox"
                    checked={researchMode}
                    onChange={(e) => setResearchMode(e.target.checked)}
                    disabled={busy}
                    style={{
                      width: '18px',
                      height: '18px',
                      cursor: 'pointer',
                      accentColor: '#6366f1'
                    }}
                  />
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    {researchMode ? '🔬 Research Mode' : '💬 Chat Mode'}
                  </span>
                </label>
                <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>
                  {researchMode ? 'Deep web search & analysis' : 'Quick AI responses'}
                </span>
              </div>
            </div>
            <button 
              type="submit" 
              disabled={busy || !inputValue.trim()}
              style={{ 
                height: 'auto',
                width: '100%'
              }}
            >
              {busy ? (researchMode ? "Researching..." : "Thinking...") : (researchMode ? "Research" : "Send")}
            </button>
          </div>
          <small style={{ color: 'var(--muted)', marginTop: '0.5rem', display: 'block' }}>
            Press Enter to send, Shift+Enter for new line
          </small>
        </form>
      </div>

      {/* Execution Logs - Collapsible */}
      {logs.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <details>
            <summary style={{ 
              cursor: 'pointer', 
              fontWeight: '600', 
              fontSize: '1.1rem',
              WebkitTapHighlightColor: 'transparent'
            }}>
              📋 Execution Logs ({logs.length})
            </summary>
            <div style={{ marginTop: '1rem' }}>
              <Log lines={logs} />
            </div>
          </details>
        </div>
      )}
    </main>
  );
}