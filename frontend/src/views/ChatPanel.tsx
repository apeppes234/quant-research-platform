import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowUpIcon,
  CheckIcon,
  PlusIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { SendMode } from "../App";
import {
  useSessionStore,
  type ToolConfirmationState,
} from "../store/sessionStore";

type Props = {
  sessionId: string | null;
  disabled?: boolean;
  setupError?: string | null;
  onSend: (
    message: string,
    mode: SendMode,
    market: string,
  ) => Promise<void>;
  onInterrupt: (reason: string) => Promise<void>;
  onConfirmTool: (
    toolUseId: string,
    result: "allow" | "deny",
    sessionThreadId?: string,
  ) => Promise<void>;
};

const SUGGESTIONS = [
  "Backtest a momentum strategy on SPY against the 5-gate rubric",
  "Find mean-reversion signals across liquid tech names",
  "Stress-test my strategy for look-ahead and overfit bias",
  "Research factor timing conditioned on macro regimes",
];

export function ChatPanel({
  sessionId,
  disabled,
  setupError,
  onSend,
  onInterrupt,
  onConfirmTool,
}: Props) {
  const [message, setMessage] = useState("");
  const [gradedLoop, setGradedLoop] = useState(false);
  const [market, setMarket] = useState("us_all");
  const [steeringBusy, setSteeringBusy] = useState(false);
  const chat = useSessionStore((state) => state.chat);
  const confirmations = useSessionStore((state) => state.pendingConfirmations);
  const threads = useSessionStore((state) => state.threads);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const hasConversation = chat.length > 0;
  const workers = Object.values(threads).filter(
    (thread) => thread.status === "running" || thread.status === "created",
  );

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [chat.length, confirmations.length, workers.length]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || disabled) return;
    setMessage("");
    await onSend(trimmed, gradedLoop ? "outcome" : "message", market);
  };

  const stop = async () => {
    if (!sessionId || steeringBusy) return;
    setSteeringBusy(true);
    try {
      await onInterrupt("stop");
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

  const composer = (
    <form className="composer-bar" onSubmit={submit}>
      <div className="composer-bar__field">
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="composer-bar__add"
          aria-label="Add context"
          onClick={() => inputRef.current?.focus()}
        >
          <PlusIcon />
        </Button>
        <Textarea
          ref={inputRef}
          className="composer-bar__input"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit(event);
            }
          }}
          placeholder="Message the research manager…"
          rows={1}
          disabled={disabled}
        />
        <Select value={market} onValueChange={setMarket} disabled={disabled}>
          <SelectTrigger
            size="sm"
            className="market-select"
            aria-label="Market universe"
          >
            <SelectValue placeholder="Select a market" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel>Universe</SelectLabel>
              <SelectItem value="us_all">Entire US stock market</SelectItem>
              <SelectItem value="spy">S&amp;P 500 · SPY</SelectItem>
              <SelectItem value="qqq">Nasdaq 100 · QQQ</SelectItem>
              <SelectItem value="iwm">Russell 2000 · IWM</SelectItem>
              <SelectItem value="single">Individual stocks</SelectItem>
              <SelectItem value="custom">Custom universe</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>
        {sessionId ? (
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="composer-bar__stop"
            aria-label="Stop"
            disabled={disabled || steeringBusy}
            onClick={() => void stop()}
          >
            <SquareIcon />
          </Button>
        ) : null}
        <Button
          type="submit"
          size="icon"
          className="composer-bar__send"
          disabled={disabled || !message.trim()}
          aria-label={gradedLoop ? "Define outcome" : "Send"}
        >
          <ArrowUpIcon />
        </Button>
      </div>
      <div className="composer-bar__controls">
        <label className="composer-toggle-inline" htmlFor="graded-loop">
          <Switch
            id="graded-loop"
            checked={gradedLoop}
            onCheckedChange={(checked) => setGradedLoop(Boolean(checked))}
            disabled={disabled}
          />
          <span>Graded loop</span>
        </label>
      </div>
    </form>
  );

  if (!hasConversation) {
    return (
      <div className="chat-page chat-page--empty">
        <div className="chat-hero">
          <div className="chat-hero__mark" aria-hidden />
          <h1 className="chat-hero__title">How can I help you today?</h1>
          <p className="chat-hero__subtitle">
            Describe a strategy or research question. Managed agents will design,
            backtest, and audit it against the overfit rubric.
          </p>
          <div className="chat-hero__composer">{composer}</div>
          <div className="chat-suggestions">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="chat-suggestion"
                disabled={disabled}
                onClick={() => setMessage(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-page">
      <div className="chat-scroll" ref={scrollRef}>
        <div className="chat-thread">
          {chat.map((item) => (
            <div
              key={item.id}
              className={`chat-message chat-message--${item.role}${item.pending ? " chat-message--pending" : ""}`}
            >
              {item.text}
            </div>
          ))}
          {setupError ? (
            <div className="setup-error" role="alert">
              <strong>Managed Agents setup needed</strong>
              <span>{setupError}</span>
              <code>make agents-apply</code>
            </div>
          ) : null}
          {confirmations.slice(-3).map((item) => (
            <div
              key={item.toolUseId}
              className={`approval-row approval-row--${item.status}`}
            >
              <div className="approval-row__body">
                <strong>{item.label}</strong>
                <Badge variant="outline">{item.toolUseId}</Badge>
                {item.input ? <code>{summarizeInput(item.input)}</code> : null}
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
          {workers.length > 0 ? (
            <div className="chat-activity" role="status" aria-live="polite">
              {workers.map((worker) => (
                <Marker key={worker.threadId}>
                  <MarkerIcon>
                    <Spinner />
                  </MarkerIcon>
                  <MarkerContent className="shimmer">
                    {worker.agentName}
                    {worker.thinking
                      ? ` · ${worker.thinking}`
                      : worker.badge
                        ? ` · ${worker.badge}`
                        : " is working…"}
                  </MarkerContent>
                </Marker>
              ))}
            </div>
          ) : null}
        </div>
      </div>
      <div className="composer-dock">{composer}</div>
    </div>
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
