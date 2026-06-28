import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("closed");
  const [sending, setSending] = useState(false);
  const applyEvent = useSessionStore((state) => state.applyEvent);
  const addLocalMessage = useSessionStore((state) => state.addLocalMessage);
  const markToolConfirmationSent = useSessionStore(
    (state) => state.markToolConfirmationSent,
  );
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
        const response = await postJson<{ sessionId: string }>(
          "/api/sessions",
          body,
        );
        setSessionId(response.sessionId);
      } else if (mode === "outcome") {
        await postJson(`/api/sessions/${sessionId}/define_outcome`, {
          description: message,
          max_iterations: 5,
        });
      } else {
        await postJson(`/api/sessions/${sessionId}/message`, {
          content: message,
        });
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
    sessionThreadId?: string,
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
      <Card className="workbench">
        <CardHeader className="topbar">
          <div>
            <CardTitle className="topbar-title">Agent Graph</CardTitle>
            <CardDescription className="topbar-subtitle">
              Managed Agents live event stream
            </CardDescription>
          </div>
          <CardAction>
            <Badge
              variant={connectionStatus === "open" ? "default" : "secondary"}
            >
              {recentEvents.length} events
            </Badge>
          </CardAction>
        </CardHeader>
        <div className="workbench-body">
          <div className="graph-pane">
            <AgentGraphCanvas />
          </div>
          <div className="analysis-lane">
            <BacktestResults sessionId={sessionId} />
            <Tabs defaultValue="iteration" className="insight-tabs">
              <TabsList className="insight-tabs__list">
                <TabsTrigger value="iteration">Iteration</TabsTrigger>
                <TabsTrigger value="ledger">Ledger</TabsTrigger>
                <TabsTrigger value="sources">Sources</TabsTrigger>
                <TabsTrigger value="report">Report</TabsTrigger>
              </TabsList>
              <TabsContent value="iteration" className="insight-tabs__content">
                <IterationPanel />
              </TabsContent>
              <TabsContent value="ledger" className="insight-tabs__content">
                <BiasLedger />
              </TabsContent>
              <TabsContent value="sources" className="insight-tabs__content">
                <ProvenanceView />
              </TabsContent>
              <TabsContent value="report" className="insight-tabs__content">
                <ReportDeliverable sessionId={sessionId} />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </Card>
      <Card className="event-panel">
        <CardHeader className="panel-header">
          <CardTitle className="panel-title">Events</CardTitle>
          <CardDescription className="panel-subtitle">
            Normalized relay tail
          </CardDescription>
        </CardHeader>
        <CardContent className="event-panel__content">
          <ScrollArea className="event-list">
            <div className="event-list__inner">
              {recentEvents.length === 0 ? (
                <div className="phase-empty">No events observed.</div>
              ) : null}
              {recentEvents.map((event) => (
                <div key={event.id} className="event-row">
                  <Badge variant="outline">{event.kind}</Badge>
                  <code>{event.type ?? event.id}</code>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
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
