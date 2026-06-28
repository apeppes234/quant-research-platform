import { FormEvent, useState } from "react";
import { CheckIcon, SendHorizontalIcon, SquareIcon, XIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldTitle,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import type { SendMode } from "../App";
import {
  useSessionStore,
  type ToolConfirmationState,
} from "../store/sessionStore";
import { ResearchSourceTab } from "./ResearchSourceTab";

type Props = {
  sessionId: string | null;
  connectionStatus: string;
  disabled?: boolean;
  onSend: (message: string, mode: SendMode) => Promise<void>;
  onInterrupt: (reason: string) => Promise<void>;
  onConfirmTool: (
    toolUseId: string,
    result: "allow" | "deny",
    sessionThreadId?: string,
  ) => Promise<void>;
};

export function ChatSteering({
  sessionId,
  connectionStatus,
  disabled,
  onSend,
  onInterrupt,
  onConfirmTool,
}: Props) {
  const [message, setMessage] = useState("");
  const [gradedLoop, setGradedLoop] = useState(true);
  const [redirect, setRedirect] = useState("");
  const [steeringBusy, setSteeringBusy] = useState(false);
  const chat = useSessionStore((state) => state.chat);
  const confirmations = useSessionStore((state) => state.pendingConfirmations);
  const sourceCount = useSessionStore((state) => state.provenance.length);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || disabled) return;
    setMessage("");
    await onSend(trimmed, gradedLoop ? "outcome" : "message");
  };

  const submitInterrupt = async (event: FormEvent) => {
    event.preventDefault();
    if (!sessionId || disabled || steeringBusy) return;
    setSteeringBusy(true);
    try {
      await onInterrupt(redirect.trim() || "stop");
      setRedirect("");
    } finally {
      setSteeringBusy(false);
    }
  };

  const confirm = async (
    item: ToolConfirmationState,
    result: "allow" | "deny",
  ) => {
    if (!sessionId || disabled || steeringBusy) return;
    setSteeringBusy(true);
    try {
      await onConfirmTool(item.toolUseId, result, item.sessionThreadId);
    } finally {
      setSteeringBusy(false);
    }
  };

  return (
    <Card className="chat-panel" data-testid="chat-steering">
      <CardHeader className="panel-header">
        <div>
          <CardTitle className="panel-title">Research Manager</CardTitle>
          <CardDescription className="panel-subtitle">
            {sessionId ?? "no session"}
          </CardDescription>
        </div>
        <CardAction className="connection-state">
          <span
            className={`connection-dot connection-dot--${connectionStatus}`}
          />
          <Badge
            variant={connectionStatus === "open" ? "default" : "secondary"}
          >
            {connectionStatus}
          </Badge>
        </CardAction>
      </CardHeader>
      <Tabs defaultValue="steering" className="sidebar-tabs">
        <TabsList className="sidebar-tabs__list">
          <TabsTrigger value="steering">Steering</TabsTrigger>
          <TabsTrigger value="research">
            Research
            {sourceCount > 0 ? (
              <Badge variant="secondary" className="sidebar-tabs__count">
                {sourceCount}
              </Badge>
            ) : null}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="steering" className="sidebar-tabs__content">
          <CardContent className="chat-panel__content">
            <ScrollArea className="chat-log">
              <div className="chat-log__inner">
                {chat.length === 0 ? (
                  <div className="chat-empty">Send a message to begin</div>
                ) : null}
                {chat.map((item) => (
                  <div
                    key={item.id}
                    className={`chat-message chat-message--${item.role}${item.pending ? " chat-message--pending" : ""}`}
                  >
                    {item.text}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
          {confirmations.length > 0 ? (
            <div className="approval-stack" aria-label="Gated tool approvals">
              {confirmations.slice(-3).map((item) => (
                <div
                  key={item.toolUseId}
                  className={`approval-row approval-row--${item.status}`}
                >
                  <div className="approval-row__body">
                    <strong>{item.label}</strong>
                    <Badge variant="outline">{item.toolUseId}</Badge>
                    {item.input ? (
                      <code>{summarizeInput(item.input)}</code>
                    ) : null}
                  </div>
                  <div className="approval-row__actions">
                    {item.status === "waiting" ? (
                      <>
                        <Button
                          type="button"
                          size="sm"
                          disabled={disabled || steeringBusy}
                          onClick={() => void confirm(item, "allow")}
                        >
                          <CheckIcon data-icon="inline-start" />
                          Approve
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          disabled={disabled || steeringBusy}
                          onClick={() => void confirm(item, "deny")}
                        >
                          <XIcon data-icon="inline-start" />
                          Deny
                        </Button>
                      </>
                    ) : (
                      <Badge
                        variant={
                          item.status === "denied" ? "destructive" : "secondary"
                        }
                      >
                        {item.status}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          <form className="interrupt-bar" onSubmit={submitInterrupt}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="interrupt-reason" className="sr-only">
                  Redirect or stop reason
                </FieldLabel>
                <div className="interrupt-bar__row">
                  <Input
                    id="interrupt-reason"
                    value={redirect}
                    onChange={(event) => setRedirect(event.target.value)}
                    placeholder="Redirect or stop reason"
                    disabled={!sessionId || disabled || steeringBusy}
                  />
                  <Button
                    type="submit"
                    variant="destructive"
                    disabled={!sessionId || disabled || steeringBusy}
                  >
                    <SquareIcon data-icon="inline-start" />
                    Stop
                  </Button>
                </div>
              </Field>
            </FieldGroup>
          </form>
          <Separator />
          <form className="composer" onSubmit={submit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="research-message" className="sr-only">
                  Research request
                </FieldLabel>
                <Textarea
                  id="research-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Backtest this starter strategy against the 5-gate rubric"
                  rows={4}
                  disabled={disabled}
                />
              </Field>
              <Field orientation="horizontal" className="composer-toggle">
                <Switch
                  id="graded-loop"
                  checked={gradedLoop}
                  onCheckedChange={(checked) => setGradedLoop(Boolean(checked))}
                  disabled={disabled}
                />
                <FieldContent>
                  <FieldTitle>Graded loop</FieldTitle>
                  <FieldDescription>
                    Send as user.define_outcome
                  </FieldDescription>
                </FieldContent>
              </Field>
            </FieldGroup>
            <CardFooter className="composer-footer">
              <Button type="submit" disabled={disabled || !message.trim()}>
                <SendHorizontalIcon data-icon="inline-start" />
                {gradedLoop ? "Define Outcome" : "Send"}
              </Button>
            </CardFooter>
          </form>
        </TabsContent>
        <TabsContent value="research" className="sidebar-tabs__content">
          <ResearchSourceTab />
        </TabsContent>
      </Tabs>
    </Card>
  );
}

function summarizeInput(input: unknown): string {
  if (typeof input === "string") return input.slice(0, 160);
  try {
    return JSON.stringify(input).slice(0, 160);
  } catch {
    return String(input).slice(0, 160);
  }
}
