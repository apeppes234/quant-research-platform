// Top-level layout: agent-graph canvas (center) + inspector/iteration/backtest/ledger/chat/provenance
// panels around it. Wires the websocket on mount. STATUS: scaffold.
//
// Layout sketch:
//   ┌───────────────┬───────────────────────────────┬───────────────┐
//   │ ChatSteering  │        AgentGraphCanvas        │ AgentInspector│
//   ├───────────────┴───────────────┬───────────────┴───────────────┤
//   │ IterationPanel │ BiasLedger    │ BacktestResults / Provenance  │
//   └───────────────────────────────┴───────────────────────────────┘
import { AgentGraphCanvas } from "./views/AgentGraphCanvas";
// import { AgentInspector } from "./views/AgentInspector";
// import { IterationPanel } from "./views/IterationPanel";
// import { BacktestResults } from "./views/BacktestResults";
// import { BiasLedger } from "./views/BiasLedger";
// import { ChatSteering } from "./views/ChatSteering";
// import { ProvenanceView } from "./views/ProvenanceView";

export function App() {
  // TODO: connect ws (src/api/ws.ts) for the active session id; feed sessionStore.
  return <AgentGraphCanvas />;
}
