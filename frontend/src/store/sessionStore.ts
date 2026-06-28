import { create } from "zustand";
import type { NormalizedEvent } from "../api/ws";

export type ThreadStatus = "created" | "running" | "idle" | "terminated";

export type ThreadState = {
  threadId: string;
  agentName: string;
  status: ThreadStatus;
  badge?: string;
  thinking?: string;
  tokens: number;
  lastEventAt?: string | null;
};

export type EdgeDirection = "delegate" | "result" | "artifact";

export type EdgeState = {
  id: string;
  fromThreadId: string;
  toThreadId: string;
  direction: EdgeDirection;
  label?: string;
  artifactIds?: string[];
  animatingUntil: number;
};

export type ArtifactKind =
  | "features"
  | "manifest"
  | "algo"
  | "results"
  | "audit"
  | "report"
  | "artifact";

export type ArtifactState = {
  id: string;
  name: string;
  path: string;
  kind: ArtifactKind;
  fromThreadId?: string;
  toThreadId?: string;
  writtenAt: string;
  animatingUntil: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "agent" | "system";
  text: string;
  pending?: boolean;
};

export type ToolConfirmationStatus =
  "waiting" | "sent" | "acknowledged" | "denied";

export type ToolConfirmationState = {
  eventId: string;
  toolUseId: string;
  threadId?: string;
  sessionThreadId?: string;
  tool: string;
  label: string;
  input?: unknown;
  status: ToolConfirmationStatus;
  result?: "allow" | "deny";
  requestedAt: string;
  processedAt?: string | null;
};

export type CurvePoint = {
  time: string;
  value: number;
};

export type BacktestSegment = {
  start?: string;
  end?: string;
  metrics?: Record<string, number | string>;
  equity_curve?: CurvePoint[];
  drawdown?: CurvePoint[];
};

export type BacktestState = {
  project_id?: string;
  backtest_id?: string;
  strategy?: string;
  segments?: Record<string, BacktestSegment>;
  rawUpdates?: Record<string, unknown>;
} | null;

export type CriterionStatus = "unknown" | "running" | "pass" | "fail";

export type RubricCriterionState = {
  id: string;
  label: string;
  condition: string;
  status: CriterionStatus;
  explanation?: string;
};

export type OutcomeState = {
  iteration: number;
  running: boolean;
  result?: string;
  explanation?: string;
  criteria: RubricCriterionState[];
};

export type LedgerEntry = {
  ts?: string;
  session_id?: string;
  variant_id?: string;
  kind?: "iteration" | "optimization" | string;
  params?: Record<string, unknown>;
  in_sample_sharpe?: number;
  holdout_sharpe?: number;
  trials_to_date?: number;
  deflated_sharpe_ratio?: number;
  path?: string;
};

export type ProvenanceProvider =
  | "arxiv"
  | "ssrn"
  | "quantresearch_repo"
  | "quantconnect_strategy_library"
  | "other";

export type ProvenanceCitation = {
  id: string;
  text: string;
  source: string;
  citation: string;
  corpus?: string;
  score?: number;
  metadata?: Record<string, unknown>;
  seenAt: string;
  // Structured fields used by the Research tab (filled from the result row or its ingestion metadata).
  provider: ProvenanceProvider;
  title?: string;
  sourceUrl?: string;
  pdfUrl?: string;
  localPdfPath?: string;
  sourcePath?: string;
  tags: string[];
  pageNumber?: number;
  threadId?: string;
  agentName?: string;
  cellIndex?: number;
  cellType?: string;
};

export type SessionState = {
  sessionStatus: string;
  threads: Record<string, ThreadState>;
  edges: EdgeState[];
  artifacts: Record<string, ArtifactState>;
  outcome: OutcomeState;
  backtest: BacktestState;
  ledger: LedgerEntry[];
  chat: ChatMessage[];
  provenance: ProvenanceCitation[];
  pendingConfirmations: ToolConfirmationState[];
  recentEvents: NormalizedEvent[];
};

export type SessionStore = SessionState & {
  applyEvent: (event: NormalizedEvent) => void;
  addLocalMessage: (text: string) => void;
  markToolConfirmationSent: (
    toolUseId: string,
    result: "allow" | "deny",
  ) => void;
  setBacktestResults: (results: BacktestState) => void;
  reset: () => void;
};

export const initialState: SessionState = {
  sessionStatus: "idle",
  threads: {},
  edges: [],
  artifacts: {},
  outcome: { iteration: 0, running: false, criteria: defaultRubricCriteria() },
  backtest: null,
  ledger: [],
  chat: [],
  provenance: [],
  pendingConfirmations: [],
  recentEvents: [],
};

export const useSessionStore = create<SessionStore>((set) => ({
  ...initialState,
  applyEvent: (event) => set((state) => reduce(state, event)),
  addLocalMessage: (text) =>
    set((state) => ({
      chat: [
        ...state.chat,
        {
          id: `local:${Date.now()}`,
          role: "user" as const,
          text,
          pending: true,
        },
      ].slice(-40),
    })),
  markToolConfirmationSent: (toolUseId, result) =>
    set((state) => ({
      pendingConfirmations: updateToolConfirmationStatus(
        state.pendingConfirmations,
        toolUseId,
        result === "deny" ? "denied" : "sent",
        result,
      ),
    })),
  setBacktestResults: (results) =>
    set({ backtest: normalizeBacktest(results) }),
  reset: () => set(initialState),
}));

export function reduce(state: SessionState, e: NormalizedEvent): SessionState {
  const recentEvents = [e, ...state.recentEvents].slice(0, 30);
  const payload = e.payload;

  switch (e.kind) {
    case "node.add": {
      const threadId = stringValue(payload.threadId);
      if (!threadId) return { ...state, recentEvents };
      const now = Date.now();
      const threads = {
        ...state.threads,
        [threadId]: {
          threadId,
          agentName: stringValue(payload.agentName) || "Agent",
          status: "created" as const,
          tokens: state.threads[threadId]?.tokens ?? 0,
          lastEventAt: stringValue((e as { processedAt?: string }).processedAt),
        },
      };
      const artifacts = reconcileArtifactTargets(threads, state.artifacts, now);
      const resolvedEdges = artifactEdgesForResolvedTargets(
        state.artifacts,
        artifacts,
        e.id,
      );
      return {
        ...state,
        recentEvents,
        threads,
        artifacts,
        edges:
          resolvedEdges.length > 0
            ? [...state.edges, ...resolvedEdges].slice(-50)
            : state.edges,
      };
    }
    case "node.status": {
      const threadId = stringValue(payload.threadId);
      if (!threadId) return { ...state, recentEvents };
      const existing = state.threads[threadId] ?? {
        threadId,
        agentName: "Agent",
        status: "created",
        tokens: 0,
      };
      return {
        ...state,
        recentEvents,
        threads: {
          ...state.threads,
          [threadId]: {
            ...existing,
            status: statusValue(payload.status),
            lastEventAt: stringValue(
              (e as { processedAt?: string }).processedAt,
            ),
          },
        },
      };
    }
    case "session.status":
      return {
        ...state,
        recentEvents,
        sessionStatus: stringValue(payload.status) || state.sessionStatus,
      };
    case "edge.animate": {
      const fromThreadId = stringValue(payload.fromThreadId);
      const toThreadId = stringValue(payload.toThreadId);
      if (!fromThreadId || !toThreadId) return { ...state, recentEvents };
      const edge: EdgeState = {
        id: `${e.id}:${fromThreadId}:${toThreadId}`,
        fromThreadId,
        toThreadId,
        direction: payload.direction === "result" ? "result" : "delegate",
        label: stringValue(payload.content),
        animatingUntil: Date.now() + 2500,
      };
      return {
        ...state,
        recentEvents,
        edges: [...state.edges, edge].slice(-40),
      };
    }
    case "artifact.write": {
      const artifact = artifactFromPayload(payload, state.threads);
      if (!artifact) return { ...state, recentEvents };
      const artifactId = artifact.id;
      const artifacts = { ...state.artifacts, [artifactId]: artifact };
      const badgeThreadId = artifact.fromThreadId;
      const threads =
        badgeThreadId && state.threads[badgeThreadId]
          ? {
              ...state.threads,
              [badgeThreadId]: {
                ...state.threads[badgeThreadId],
                badge: stringValue(payload.label) || `Writing ${artifact.name}`,
              },
            }
          : state.threads;
      const edge =
        artifact.fromThreadId && artifact.toThreadId
          ? {
              id: `${e.id}:${artifact.fromThreadId}:${artifact.toThreadId}:${artifact.id}`,
              fromThreadId: artifact.fromThreadId,
              toThreadId: artifact.toThreadId,
              direction: "artifact" as const,
              label: artifact.name,
              artifactIds: [artifact.id],
              animatingUntil: artifact.animatingUntil,
            }
          : null;
      return {
        ...state,
        recentEvents,
        threads,
        artifacts,
        edges: edge ? [...state.edges, edge].slice(-50) : state.edges,
      };
    }
    case "node.badge": {
      const threadId = stringValue(payload.threadId);
      if (!threadId || !state.threads[threadId])
        return { ...state, recentEvents };
      return {
        ...state,
        recentEvents,
        threads: {
          ...state.threads,
          [threadId]: {
            ...state.threads[threadId],
            badge: stringValue(payload.label),
          },
        },
      };
    }
    case "agent.text": {
      const text = stringValue(payload.text);
      return {
        ...state,
        recentEvents,
        chat: text
          ? [...state.chat, { id: e.id, role: "agent" as const, text }].slice(
              -40,
            )
          : state.chat,
      };
    }
    case "agent.thinking": {
      const threadId = stringValue(payload.threadId);
      if (!threadId || !state.threads[threadId])
        return { ...state, recentEvents };
      return {
        ...state,
        recentEvents,
        threads: {
          ...state.threads,
          [threadId]: {
            ...state.threads[threadId],
            thinking: stringValue(payload.text),
          },
        },
      };
    }
    case "cost.add": {
      const threadId = stringValue(payload.threadId);
      if (!threadId || !state.threads[threadId])
        return { ...state, recentEvents };
      const usage = payload.usage as
        { input_tokens?: number; output_tokens?: number } | undefined;
      const delta =
        Number(usage?.input_tokens ?? 0) + Number(usage?.output_tokens ?? 0);
      return {
        ...state,
        recentEvents,
        threads: {
          ...state.threads,
          [threadId]: {
            ...state.threads[threadId],
            tokens: state.threads[threadId].tokens + delta,
          },
        },
      };
    }
    case "rubric.start":
      return {
        ...state,
        recentEvents,
        outcome: applyRubricPayload(state.outcome, payload, "running"),
      };
    case "rubric.ongoing":
      return {
        ...state,
        recentEvents,
        outcome: applyRubricPayload(state.outcome, payload, "running"),
      };
    case "rubric.end":
      return {
        ...state,
        recentEvents,
        outcome: applyRubricPayload(state.outcome, payload, "ended"),
      };
    case "backtest.update":
      return {
        ...state,
        recentEvents,
        backtest: mergeBacktestUpdate(state.backtest, payload),
      };
    case "ledger.entry":
      return {
        ...state,
        recentEvents,
        ledger: upsertLedgerEntry(state.ledger, payload),
      };
    case "provenance.add":
      return {
        ...state,
        recentEvents,
        provenance: mergeProvenance(state.provenance, payload, state.threads),
      };
    case "tool.confirmation.requested":
      return {
        ...state,
        recentEvents,
        pendingConfirmations: upsertToolConfirmation(
          state.pendingConfirmations,
          payload,
          e,
        ),
      };
    case "user.event":
      return applyUserEvent({ ...state, recentEvents }, payload, e);
    case "relay.error":
      return {
        ...state,
        recentEvents,
        chat: [
          ...state.chat,
          {
            id: e.id,
            role: "system" as const,
            text: stringValue(payload.message) || "Event stream error",
          },
        ].slice(-40),
      };
    default:
      return { ...state, recentEvents };
  }
}

export function defaultRubricCriteria(): RubricCriterionState[] {
  return [
    {
      id: "holdout_sharpe",
      label: "Out-of-sample performance",
      condition: "Holdout Sharpe > 1.0",
      status: "unknown",
    },
    {
      id: "is_oos_gap",
      label: "Overfit guard",
      condition: "|IS Sharpe - OOS Sharpe| < 0.5",
      status: "unknown",
    },
    {
      id: "look_ahead",
      label: "Look-ahead audit",
      condition: "Zero look-ahead findings",
      status: "unknown",
    },
    {
      id: "deflated_sharpe",
      label: "Multiple-testing correction",
      condition: "Deflated Sharpe Ratio > 0",
      status: "unknown",
    },
    {
      id: "max_drawdown",
      label: "Tail risk",
      condition: "Max drawdown < 25%",
      status: "unknown",
    },
  ];
}

function applyUserEvent(
  state: SessionState,
  payload: Record<string, unknown>,
  event: NormalizedEvent,
): SessionState {
  const userEventType = stringValue(payload.userEventType);
  const content = stringValue(payload.content);
  const processed = payload.processed === true;

  if (userEventType === "user.tool_confirmation") {
    const toolUseId = stringValue(payload.toolUseId);
    const result = confirmationResult(payload.result);
    return {
      ...state,
      pendingConfirmations: toolUseId
        ? updateToolConfirmationStatus(
            state.pendingConfirmations,
            toolUseId,
            processed
              ? result === "deny"
                ? "denied"
                : "acknowledged"
              : "sent",
            result,
          )
        : state.pendingConfirmations,
      chat: [
        ...state.chat,
        {
          id: event.id,
          role: "system" as const,
          text: `Tool ${result === "deny" ? "denied" : "approved"}${processed ? "" : " (queued)"}`,
          pending: !processed,
        },
      ].slice(-40),
    };
  }

  if (userEventType === "user.interrupt") {
    return {
      ...state,
      chat: [
        ...state.chat,
        {
          id: event.id,
          role: "system" as const,
          text: content ? `Interrupt sent: ${content}` : "Interrupt sent",
          pending: !processed,
        },
      ].slice(-40),
    };
  }

  if (
    userEventType === "user.message" ||
    userEventType === "user.define_outcome"
  ) {
    return {
      ...state,
      chat: reconcileUserMessage(state.chat, event.id, content, processed),
    };
  }

  return state;
}

function reconcileUserMessage(
  current: ChatMessage[],
  eventId: string,
  content: string,
  processed: boolean,
): ChatMessage[] {
  if (!content) return current;
  const pendingIndex = current.findIndex(
    (message) =>
      message.role === "user" && message.pending && message.text === content,
  );
  if (pendingIndex >= 0) {
    return current.map((message, index) =>
      index === pendingIndex
        ? { ...message, id: eventId, pending: !processed }
        : message,
    );
  }
  if (current.some((message) => message.id === eventId)) return current;
  return [
    ...current,
    { id: eventId, role: "user" as const, text: content, pending: !processed },
  ].slice(-40);
}

function upsertToolConfirmation(
  current: ToolConfirmationState[],
  payload: Record<string, unknown>,
  event: NormalizedEvent,
): ToolConfirmationState[] {
  const item = toolConfirmationFromPayload(payload, event);
  if (!item) return current;
  const filtered = current.filter(
    (confirmation) => confirmation.toolUseId !== item.toolUseId,
  );
  return [...filtered, item].slice(-20);
}

function toolConfirmationFromPayload(
  payload: Record<string, unknown>,
  event: NormalizedEvent,
): ToolConfirmationState | null {
  const toolUseId = stringValue(payload.toolUseId) || event.id;
  const tool = stringValue(payload.tool) || "tool";
  if (!toolUseId) return null;
  return {
    eventId: event.id,
    toolUseId,
    threadId: stringValue(payload.threadId),
    sessionThreadId:
      stringValue(payload.sessionThreadId) || stringValue(payload.threadId),
    tool,
    label: stringValue(payload.label) || `Approve ${tool}`,
    input: payload.input,
    status: "waiting",
    requestedAt: new Date().toISOString(),
    processedAt: event.processedAt ?? null,
  };
}

function updateToolConfirmationStatus(
  current: ToolConfirmationState[],
  toolUseId: string,
  status: ToolConfirmationStatus,
  result?: "allow" | "deny",
): ToolConfirmationState[] {
  return current.map((confirmation) =>
    confirmation.toolUseId === toolUseId
      ? {
          ...confirmation,
          status,
          result,
          processedAt:
            status === "acknowledged" || status === "denied"
              ? new Date().toISOString()
              : confirmation.processedAt,
        }
      : confirmation,
  );
}

function confirmationResult(value: unknown): "allow" | "deny" {
  return value === "deny" ? "deny" : "allow";
}

function applyRubricPayload(
  current: OutcomeState,
  payload: Record<string, unknown>,
  phase: "running" | "ended",
): OutcomeState {
  const iteration =
    Number(payload.iteration ?? current.iteration) || current.iteration;
  const incoming = criteriaFromPayload(payload.criteria);
  const result = stringValue(payload.result) || current.result;
  const explanation = stringValue(payload.explanation) || current.explanation;
  const criteria =
    incoming.length > 0
      ? mergeCriteria(current.criteria, incoming, phase)
      : phase === "running"
        ? current.criteria.map((criterion) => ({
            ...criterion,
            status:
              criterion.status === "unknown"
                ? ("running" as const)
                : criterion.status,
          }))
        : current.criteria;
  return {
    iteration,
    running: phase === "running",
    result: phase === "ended" ? result : undefined,
    explanation,
    criteria,
  };
}

function criteriaFromPayload(value: unknown): RubricCriterionState[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item): RubricCriterionState | null => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      const id = stringValue(row.id);
      const label = stringValue(row.label);
      if (!id || !label) return null;
      return {
        id,
        label,
        condition:
          stringValue(row.condition) || stringValue(row.pass_condition),
        status: criterionStatus(row.status),
        explanation: stringValue(row.explanation),
      };
    })
    .filter((item): item is RubricCriterionState => Boolean(item));
}

function mergeCriteria(
  current: RubricCriterionState[],
  incoming: RubricCriterionState[],
  phase: "running" | "ended",
): RubricCriterionState[] {
  const byId = new Map(current.map((criterion) => [criterion.id, criterion]));
  for (const criterion of incoming) {
    const existing = byId.get(criterion.id);
    byId.set(criterion.id, {
      ...(existing ?? criterion),
      ...criterion,
      status:
        criterion.status === "unknown" && phase === "running"
          ? existing?.status === "pass" || existing?.status === "fail"
            ? existing.status
            : "running"
          : criterion.status,
    });
  }
  return defaultRubricCriteria().map(
    (criterion) => byId.get(criterion.id) ?? criterion,
  );
}

function criterionStatus(value: unknown): CriterionStatus {
  if (value === "pass" || value === "fail" || value === "running") return value;
  return "unknown";
}

function upsertLedgerEntry(
  current: LedgerEntry[],
  payload: Record<string, unknown>,
): LedgerEntry[] {
  const entry = ledgerEntryFromPayload(payload.entry);
  if (!entry) return current;
  const key = ledgerKey(entry);
  const filtered = current.filter((item) => ledgerKey(item) !== key);
  return [...filtered, entry].slice(-80);
}

function ledgerEntryFromPayload(value: unknown): LedgerEntry | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  return {
    ts: stringValue(row.ts) || new Date().toISOString(),
    session_id: stringValue(row.session_id),
    variant_id: stringValue(row.variant_id) || stringValue(row.id),
    kind: stringValue(row.kind),
    params: objectValue(row.params),
    in_sample_sharpe: numberValue(row.in_sample_sharpe),
    holdout_sharpe: numberValue(row.holdout_sharpe),
    trials_to_date: numberValue(row.trials_to_date),
    deflated_sharpe_ratio: numberValue(row.deflated_sharpe_ratio),
    path: stringValue(row.path),
  };
}

function ledgerKey(entry: LedgerEntry): string {
  return entry.variant_id || `${entry.path ?? "ledger"}:${entry.ts ?? ""}`;
}

function mergeProvenance(
  current: ProvenanceCitation[],
  payload: Record<string, unknown>,
  threads: Record<string, ThreadState>,
): ProvenanceCitation[] {
  const threadId = stringValue(payload.threadId);
  const agentName =
    stringValue(payload.agentName) || threads[threadId]?.agentName || "";
  const citations = citationsFromPayload(payload.citations, {
    threadId,
    agentName,
  });
  if (citations.length === 0) return current;
  const byId = new Map(current.map((citation) => [citation.id, citation]));
  for (const citation of citations) {
    // keep the agent attribution from the first sighting if a later one lacks it
    const existing = byId.get(citation.id);
    byId.set(citation.id, {
      ...citation,
      agentName: citation.agentName || existing?.agentName,
      threadId: citation.threadId || existing?.threadId,
    });
  }
  return Array.from(byId.values()).slice(-120);
}

function citationsFromPayload(
  value: unknown,
  context: { threadId?: string; agentName?: string },
): ProvenanceCitation[] {
  if (!Array.isArray(value)) return [];
  const now = new Date().toISOString();
  return value
    .map((item): ProvenanceCitation | null => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      const meta = objectValue(row.metadata) ?? {};
      const pick = (key: string): unknown =>
        row[key] !== undefined && row[key] !== null ? row[key] : meta[key];

      const citation = stringValue(row.citation);
      const source = stringValue(row.source);
      if (!citation && !source) return null;
      const corpus = stringValue(row.corpus) || stringValue(meta.corpus);
      const provider = normalizeProvider(
        stringValue(pick("provider")),
        corpus,
        source,
      );

      return {
        id: `${citation || source}:${corpus}`,
        text: stringValue(row.text) || stringValue(pick("snippet")),
        source,
        citation,
        corpus,
        score: numberValue(row.score),
        metadata: objectValue(row.metadata),
        seenAt: now,
        provider,
        title: stringValue(pick("title")) || undefined,
        sourceUrl:
          stringValue(pick("source_url")) ||
          (isUrl(source) ? source : undefined),
        pdfUrl: stringValue(pick("pdf_url")) || undefined,
        localPdfPath: stringValue(pick("local_pdf_path")) || undefined,
        sourcePath: stringValue(pick("source_path")) || undefined,
        tags: stringList(pick("tags")),
        pageNumber: numberValue(pick("page_number") ?? pick("pageNumber")),
        threadId: context.threadId || undefined,
        agentName: context.agentName || undefined,
        cellIndex: numberValue(meta.cell_index),
        cellType: stringValue(meta.cell_type) || undefined,
      };
    })
    .filter((item): item is ProvenanceCitation => Boolean(item));
}

function normalizeProvider(
  raw: string,
  corpus: string,
  source: string,
): ProvenanceProvider {
  const value = raw.toLowerCase();
  if (value.includes("arxiv")) return "arxiv";
  if (value.includes("ssrn")) return "ssrn";
  if (value.includes("quantresearch")) return "quantresearch_repo";
  if (value.includes("quantconnect") || value.includes("strategy_library"))
    return "quantconnect_strategy_library";
  // fall back to corpus/source hints
  const lowerSource = source.toLowerCase();
  if (lowerSource.includes("arxiv")) return "arxiv";
  if (lowerSource.includes("ssrn")) return "ssrn";
  if (corpus === "repo") return "quantresearch_repo";
  if (corpus === "strategy_library") return "quantconnect_strategy_library";
  return "other";
}

function isUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function stringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map((tag) => String(tag))
      .filter((tag) => tag.trim().length > 0);
  }
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberValue(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}

function objectValue(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function statusValue(value: unknown): ThreadStatus {
  if (value === "running" || value === "idle" || value === "terminated") {
    return value;
  }
  return "created";
}

function normalizeBacktest(value: BacktestState): BacktestState {
  if (!value || typeof value !== "object") return null;
  return value;
}

function mergeBacktestUpdate(
  current: BacktestState,
  payload: Record<string, unknown>,
): BacktestState {
  const result = payload.result;
  if (isBacktestState(result) && result.segments) {
    return result;
  }
  const tool = stringValue(payload.tool) || "unknown";
  return {
    ...(current ?? {}),
    rawUpdates: {
      ...(current?.rawUpdates ?? {}),
      [tool]: result,
    },
  };
}

function isBacktestState(
  value: unknown,
): value is Exclude<BacktestState, null> {
  return Boolean(value && typeof value === "object");
}

function artifactFromPayload(
  payload: Record<string, unknown>,
  threads: Record<string, ThreadState>,
): ArtifactState | null {
  const raw = payload.artifact;
  if (!raw || typeof raw !== "object") return null;
  const artifact = raw as Record<string, unknown>;
  const path = stringValue(artifact.path);
  const name = stringValue(artifact.name) || fileName(path);
  if (!path || !name) return null;
  const fromThreadId = stringValue(payload.threadId);
  const kind = artifactKind(stringValue(artifact.kind), name);
  const toThreadId =
    stringValue(payload.toThreadId) ||
    inferArtifactTarget(threads, kind, fromThreadId);
  return {
    id: path,
    name,
    path,
    kind,
    fromThreadId: fromThreadId || undefined,
    toThreadId: toThreadId || undefined,
    writtenAt: new Date().toISOString(),
    animatingUntil: Date.now() + 3200,
  };
}

function fileName(path: string): string {
  const parts = path.split("/").filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : "";
}

function artifactKind(value: string, name: string): ArtifactKind {
  if (
    value === "features" ||
    value === "manifest" ||
    value === "algo" ||
    value === "results" ||
    value === "audit" ||
    value === "report"
  ) {
    return value;
  }
  if (name.startsWith("features") && name.endsWith(".parquet"))
    return "features";
  if (name === "data_manifest.json") return "manifest";
  if (name === "algo.py") return "algo";
  if (name === "results.json") return "results";
  if (name === "audit.json") return "audit";
  if (name === "report.pdf") return "report";
  return "artifact";
}

function inferArtifactTarget(
  threads: Record<string, ThreadState>,
  kind: ArtifactKind,
  fromThreadId?: string,
): string {
  const hints: Record<ArtifactKind, string[]> = {
    features: ["feature", "modeling"],
    manifest: ["modeling"],
    algo: ["backtest"],
    results: ["risk"],
    audit: ["research manager", "manager"],
    report: ["research manager", "manager"],
    artifact: [],
  };
  const candidates = Object.values(threads);
  for (const hint of hints[kind]) {
    const match = candidates.find(
      (thread) =>
        thread.threadId !== fromThreadId &&
        thread.agentName.toLowerCase().includes(hint),
    );
    if (match) return match.threadId;
  }
  return "";
}

function reconcileArtifactTargets(
  threads: Record<string, ThreadState>,
  artifacts: Record<string, ArtifactState>,
  now = Date.now(),
): Record<string, ArtifactState> {
  const next = { ...artifacts };
  for (const artifact of Object.values(next)) {
    if (!artifact.toThreadId) {
      const toThreadId = inferArtifactTarget(
        threads,
        artifact.kind,
        artifact.fromThreadId,
      );
      if (toThreadId) {
        next[artifact.id] = {
          ...artifact,
          toThreadId,
          animatingUntil: now + 3200,
        };
      }
    }
  }
  return next;
}

function artifactEdgesForResolvedTargets(
  previous: Record<string, ArtifactState>,
  next: Record<string, ArtifactState>,
  eventId: string,
): EdgeState[] {
  return Object.values(next)
    .filter(
      (artifact) =>
        artifact.fromThreadId &&
        artifact.toThreadId &&
        !previous[artifact.id]?.toThreadId,
    )
    .map((artifact) => ({
      id: `${eventId}:${artifact.fromThreadId}:${artifact.toThreadId}:${artifact.id}`,
      fromThreadId: artifact.fromThreadId as string,
      toThreadId: artifact.toThreadId as string,
      direction: "artifact" as const,
      label: artifact.name,
      artifactIds: [artifact.id],
      animatingUntil: artifact.animatingUntil,
    }));
}
