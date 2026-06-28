import { FormEvent, useState } from "react";
import type { SendMode } from "../App";
import { useSessionStore, type ToolConfirmationState } from "../store/sessionStore";

type Props = {
  sessionId: string | null;
  connectionStatus: string;
  disabled?: boolean;
  onSend: (message: string, mode: SendMode) => Promise<void>;
  onInterrupt: (reason: string) => Promise<void>;
  onConfirmTool: (
    toolUseId: string,
    result: "allow" | "deny",
    sessionThreadId?: string
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

  const confirm = async (item: ToolConfirmationState, result: "allow" | "deny") => {
    if (!sessionId || disabled || steeringBusy) return;
    setSteeringBusy(true);
    try {
      await onConfirmTool(item.toolUseId, result, item.sessionThreadId);
    } finally {
      setSteeringBusy(false);
    }
  };

  return (
    <aside className="chat-panel" data-testid="chat-steering">
      <div className="panel-header">
        <div>
          <div className="panel-title">Research Manager</div>
          <div className="panel-subtitle">{sessionId ?? "no session"}</div>
        </div>
        <span className={`connection-dot connection-dot--${connectionStatus}`} />
      </div>
      <div className="chat-log">
        {chat.length === 0 ? <div className="chat-empty">Send a message to begin</div> : null}
        {chat.map((item) => (
          <div
            key={item.id}
            className={`chat-message chat-message--${item.role}${item.pending ? " chat-message--pending" : ""}`}
          >
            {item.text}
          </div>
        ))}
      </div>
      {confirmations.length > 0 ? (
        <div className="approval-stack" aria-label="Gated tool approvals">
          {confirmations.slice(-3).map((item) => (
            <div key={item.toolUseId} className={`approval-row approval-row--${item.status}`}>
              <div className="approval-row__body">
                <strong>{item.label}</strong>
                <span>{item.toolUseId}</span>
                {item.input ? <code>{summarizeInput(item.input)}</code> : null}
              </div>
              <div className="approval-row__actions">
                {item.status === "waiting" ? (
                  <>
                    <button
                      type="button"
                      className="approval-button approval-button--allow"
                      disabled={disabled || steeringBusy}
                      onClick={() => void confirm(item, "allow")}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="approval-button approval-button--deny"
                      disabled={disabled || steeringBusy}
                      onClick={() => void confirm(item, "deny")}
                    >
                      Deny
                    </button>
                  </>
                ) : (
                  <span>{item.status}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : null}
      <form className="interrupt-bar" onSubmit={submitInterrupt}>
        <input
          value={redirect}
          onChange={(event) => setRedirect(event.target.value)}
          placeholder="Redirect or stop reason"
          disabled={!sessionId || disabled || steeringBusy}
        />
        <button type="submit" disabled={!sessionId || disabled || steeringBusy}>
          Stop/Redirect
        </button>
      </form>
      <form className="composer" onSubmit={submit}>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Backtest this starter strategy against the 5-gate rubric"
          rows={3}
          disabled={disabled}
        />
        <label className="composer-toggle">
          <input
            type="checkbox"
            checked={gradedLoop}
            onChange={(event) => setGradedLoop(event.target.checked)}
            disabled={disabled}
          />
          <span>Graded loop</span>
        </label>
        <button type="submit" disabled={disabled || !message.trim()}>
          {gradedLoop ? "Define Outcome" : "Send"}
        </button>
      </form>
    </aside>
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
