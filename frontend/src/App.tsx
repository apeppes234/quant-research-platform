import { useEffect, useState } from "react";
import { connect, type ConnectionStatus } from "./api/ws";
import { useSessionStore } from "./store/sessionStore";
import { AgentGraphCanvas } from "./views/AgentGraphCanvas";
import { BacktestResults } from "./views/BacktestResults";
import { BiasLedger } from "./views/BiasLedger";
import { ChatSteering } from "./views/ChatSteering";
import { IterationPanel } from "./views/IterationPanel";
import { ProvenanceView } from "./views/ProvenanceView";
import { ReportDeliverable } from "./views/ReportDeliverable";

export type SendMode = "message" | "outcome";

export function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("closed");
  const [sending, setSending] = useState(false);
  const applyEvent = useSessionStore((state) => state.applyEvent);
  const addLocalMessage = useSessionStore((state) => state.addLocalMessage);
  const markToolConfirmationSent = useSessionStore((state) => state.markToolConfirmationSent);
  const recentEvents = useSessionStore((state) => state.recentEvents);

  useEffect(() => {
    if (!sessionId) return undefined;
    return connect(sessionId, applyEvent, setConnectionStatus);
  }, [applyEvent, sessionId]);

  const sendMessage = async (message: string, mode: SendMode) => {
    setSending(true);
    addLocalMessage(message);
    try {
      if (!sessionId) {
        const body =
          mode === "outcome"
            ? { outcome: { description: message, max_iterations: 5 } }
            : { message };
        const response = await postJson<{ sessionId: string }>("/api/sessions", body);
        setSessionId(response.sessionId);
      } else if (mode === "outcome") {
        await postJson(`/api/sessions/${sessionId}/define_outcome`, {
          description: message,
          max_iterations: 5,
        });
      } else {
        await postJson(`/api/sessions/${sessionId}/message`, { content: message });
      }
    } finally {
      setSending(false);
    }
  };

  const interrupt = async (reason: string) => {
    if (!sessionId) return;
    await postJson(`/api/sessions/${sessionId}/interrupt`, { reason });
  };

  const confirmTool = async (
    toolUseId: string,
    result: "allow" | "deny",
    sessionThreadId?: string
  ) => {
    if (!sessionId) return;
    await postJson(`/api/sessions/${sessionId}/confirm`, {
      tool_use_id: toolUseId,
      result,
      session_thread_id: sessionThreadId,
    });
    markToolConfirmationSent(toolUseId, result);
  };

  return (
    <main className="app-shell">
      <ChatSteering
        sessionId={sessionId}
        connectionStatus={connectionStatus}
        disabled={sending}
        onSend={sendMessage}
        onInterrupt={interrupt}
        onConfirmTool={confirmTool}
      />
      <section className="workbench">
        <header className="topbar">
          <div>
            <div className="topbar-title">Agent Graph</div>
            <div className="topbar-subtitle">{connectionStatus}</div>
          </div>
          <div className="event-count">{recentEvents.length} events</div>
        </header>
        <div className="workbench-body">
          <div className="graph-pane">
            <AgentGraphCanvas />
          </div>
          <div className="analysis-lane">
            <BacktestResults sessionId={sessionId} />
            <div className="insight-panels">
              <IterationPanel />
              <BiasLedger />
              <ProvenanceView />
              <ReportDeliverable sessionId={sessionId} />
            </div>
          </div>
        </div>
      </section>
      <aside className="event-panel">
        <div className="panel-header">
          <div className="panel-title">Events</div>
        </div>
        <div className="event-list">
          {recentEvents.map((event) => (
            <div key={event.id} className="event-row">
              <span>{event.kind}</span>
              <code>{event.type ?? event.id}</code>
            </div>
          ))}
        </div>
      </aside>
    </main>
  );
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}
