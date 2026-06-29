import { useEffect, useState } from "react";
import {
  BarChart3Icon,
  BookOpenIcon,
  LightbulbIcon,
  MessageSquareIcon,
  NetworkIcon,
  UsersIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { runDemoReply, runDemoSession } from "./api/demo";
import { connect, type ConnectionStatus } from "./api/ws";
import { useSessionStore } from "./store/sessionStore";
import { AgentGraphCanvas } from "./views/AgentGraphCanvas";
import { BacktestResults } from "./views/BacktestResults";
import { BiasLedger } from "./views/BiasLedger";
import { ChatPanel } from "./views/ChatPanel";
import { IterationPanel } from "./views/IterationPanel";
import { ProvenanceView } from "./views/ProvenanceView";
import { ResearchSourceTab } from "./views/ResearchSourceTab";
import { ReportDeliverable } from "./views/ReportDeliverable";
import { TeamDirectory } from "./views/TeamDirectory";

export type SendMode = "message" | "outcome";

const NAV = [
  { value: "chat", label: "Chat", icon: MessageSquareIcon },
  { value: "research", label: "Research", icon: BookOpenIcon },
  { value: "agents", label: "Agents", icon: NetworkIcon },
  { value: "team", label: "Team", icon: UsersIcon },
  { value: "results", label: "Results", icon: BarChart3Icon },
  { value: "insights", label: "Insights", icon: LightbulbIcon },
] as const;

export function App() {
  const [tab, setTab] = useState<string>("chat");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("closed");
  const [sending, setSending] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const applyEvent = useSessionStore((state) => state.applyEvent);
  const addLocalMessage = useSessionStore((state) => state.addLocalMessage);
  const markToolConfirmationSent = useSessionStore(
    (state) => state.markToolConfirmationSent,
  );
  const recentEvents = useSessionStore((state) => state.recentEvents);
  const sourceCount = useSessionStore((state) => state.provenance.length);
  const threads = useSessionStore((state) => state.threads);
  const activeAgents = Object.values(threads).filter(
    (thread) => thread.status === "running",
  ).length;

  useEffect(() => {
    if (!sessionId) return undefined;
    return connect(sessionId, applyEvent, setConnectionStatus);
  }, [applyEvent, sessionId]);

  const sendMessage = async (
    message: string,
    mode: SendMode,
    market: string,
  ) => {
    setSending(true);
    setSessionError(null);
    addLocalMessage(message);
    if (demoMode) {
      runDemoReply(applyEvent, message);
      setSending(false);
      return;
    }
    try {
      if (!sessionId) {
        const body =
          mode === "outcome"
            ? {
                outcome: { description: message, max_iterations: 5 },
                universe: market,
              }
            : { message, universe: market };
        const response = await postJson<{ sessionId: string }>(
          "/api/sessions",
          body,
        );
        setSessionId(response.sessionId);
      } else if (mode === "outcome") {
        await postJson(`/api/sessions/${sessionId}/define_outcome`, {
          description: message,
          max_iterations: 5,
          universe: market,
        });
      } else {
        await postJson(`/api/sessions/${sessionId}/message`, {
          content: message,
          universe: market,
        });
      }
    } catch (error) {
      if (shouldUseDemoFallback(error)) {
        // No orchestrator reachable — fall back to a simulated demo run so the
        // UI can be explored without a backend.
        setDemoMode(true);
        setConnectionStatus("open");
        runDemoSession(applyEvent);
      } else {
        setConnectionStatus("closed");
        setSessionError(errorMessage(error));
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

  const activeNav = NAV.find((item) => item.value === tab);

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <div className="app-brand">
            <span className="app-brand__mark" aria-hidden />
            <div className="app-brand__text">
              <span className="app-brand__name">Quant Research</span>
              <span className="app-brand__sub">Managed Agents</span>
            </div>
          </div>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {NAV.map((item) => (
                  <SidebarMenuItem key={item.value}>
                    <SidebarMenuButton
                      isActive={tab === item.value}
                      tooltip={item.label}
                      onClick={() => setTab(item.value)}
                    >
                      <item.icon />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                    {item.value === "agents" && activeAgents > 0 ? (
                      <SidebarMenuBadge>{activeAgents}</SidebarMenuBadge>
                    ) : null}
                    {item.value === "research" && sourceCount > 0 ? (
                      <SidebarMenuBadge>{sourceCount}</SidebarMenuBadge>
                    ) : null}
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <div className="app-status">
            <span
              className={`connection-dot connection-dot--${connectionStatus}`}
            />
            <span className="app-status__label">{connectionStatus}</span>
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset className="app-inset">
        <header className="app-topbar">
          <SidebarTrigger />
          <div className="app-topbar__heading">
            <span className="app-topbar__title">{activeNav?.label}</span>
            <span className="app-topbar__sub">
              {sessionId ?? "Managed Agents workspace"}
            </span>
          </div>
          <div className="app-status">
            <span
              className={`connection-dot connection-dot--${connectionStatus}`}
            />
            <Badge
              variant={connectionStatus === "open" ? "default" : "secondary"}
            >
              {connectionStatus}
            </Badge>
          </div>
        </header>

        <Tabs value={tab} onValueChange={setTab} className="app-tabs">
          <TabsContent value="chat" className="tab-pane">
            <ChatPanel
              sessionId={sessionId}
              disabled={sending}
              setupError={sessionError}
              onSend={sendMessage}
              onInterrupt={interrupt}
              onConfirmTool={confirmTool}
            />
          </TabsContent>

          <TabsContent value="research" className="tab-pane">
            <ResearchSourceTab />
          </TabsContent>

          <TabsContent value="agents" className="tab-pane">
            <div className="agents-layout">
              <div className="agents-canvas">
                <AgentGraphCanvas />
              </div>
              <aside className="agents-events">
                <div className="agents-events__header">
                  <span className="agents-events__title">Event stream</span>
                  <Badge
                    variant={
                      connectionStatus === "open" ? "default" : "secondary"
                    }
                  >
                    {recentEvents.length}
                  </Badge>
                </div>
                <ScrollArea className="agents-events__list">
                  <div className="event-list__inner">
                    {recentEvents.length === 0 ? (
                      <div className="phase-empty">No events observed yet.</div>
                    ) : null}
                    {recentEvents.map((event) => (
                      <div key={event.id} className="event-row">
                        <Badge variant="outline">{event.kind}</Badge>
                        <code>{event.type ?? event.id}</code>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </aside>
            </div>
          </TabsContent>

          <TabsContent value="team" className="tab-pane tab-pane--scroll">
            <TeamDirectory />
          </TabsContent>

          <TabsContent value="results" className="tab-pane">
            <BacktestResults sessionId={sessionId} />
          </TabsContent>

          <TabsContent value="insights" className="tab-pane">
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
          </TabsContent>
        </Tabs>
      </SidebarInset>
    </SidebarProvider>
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
    throw new ApiError(response.status, responseDetail(detail));
  }
  return (await response.json()) as T;
}

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function responseDetail(value: string): string {
  if (!value.trim()) return "Request failed";
  try {
    const parsed = JSON.parse(value) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // Keep the raw response below.
  }
  return value;
}

function shouldUseDemoFallback(error: unknown): boolean {
  if (error instanceof ApiError) {
    const message = error.message.toLowerCase();
    return (
      error.status >= 500 &&
      (message.includes("econnrefused") ||
        message.includes("failed to fetch") ||
        message.includes("proxy error"))
    );
  }
  return error instanceof TypeError;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
