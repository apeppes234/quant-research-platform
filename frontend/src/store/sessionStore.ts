// Pure reducer over normalized events ({kind,payload}) -> UI state. Keyed off `kind`, which must match
// orchestrator/app/events/schema.py NORMALIZATION. STATUS: scaffold.
//
// State shape (the views subscribe to slices):
//   threads:    Record<threadId, { agentName, status, badge?, thinking?, tokens }>
//   edges:      Array<{ from, to, dir: "delegate" | "result", animatingUntil }>
//   outcome:    { iteration: number, criteria: Array<{ name, pass: boolean | null, explanation? }> }
//   backtest:   { equityCurve, drawdown, trades, metrics }   // from QC read_backtest*
//   ledger:     Array<{ variantId, inSampleSharpe, holdoutSharpe, trials, deflatedSharpe }>
//   chat:       Array<{ role, text, pending }>
//   provenance: Array<{ source, citation }>

import type { NormalizedEvent } from "../api/ws";

export type SessionState = {
  threads: Record<string, unknown>;
  edges: unknown[];
  outcome: { iteration: number; criteria: unknown[] };
  backtest: unknown;
  ledger: unknown[];
  chat: unknown[];
  provenance: unknown[];
};

export function reduce(state: SessionState, e: NormalizedEvent): SessionState {
  switch (e.kind) {
    // case "node.add":      ...
    // case "node.status":   ...
    // case "edge.animate":  ...
    // case "node.badge":    ...
    // case "cost.add":      ...
    // case "rubric.start":  ...
    // case "rubric.end":    ...
    default:
      return state; // scaffold
  }
}
