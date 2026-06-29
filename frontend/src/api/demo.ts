import type { NormalizedEvent } from "./ws";

type Emit = (event: NormalizedEvent) => void;

let seq = 0;
const ev = (
  kind: string,
  payload: Record<string, unknown>,
): NormalizedEvent => ({
  kind,
  id: `demo-${kind}-${seq++}`,
  type: kind,
  processedAt: new Date().toISOString(),
  payload,
});

const usage = () => ({
  usage: { input_tokens: 1800 + Math.floor(Math.random() * 2600), output_tokens: 400 + Math.floor(Math.random() * 900) },
});

function series(
  count: number,
  start: number,
  driftPct: number,
  startYear: number,
): { time: string; value: number }[] {
  const rows: { time: string; value: number }[] = [];
  let value = start;
  for (let i = 0; i < count; i += 1) {
    const month = (i % 12) + 1;
    const year = startYear + Math.floor(i / 12);
    value *= 1 + driftPct + (Math.random() - 0.45) * 0.04;
    rows.push({
      time: `${year}-${String(month).padStart(2, "0")}`,
      value: Math.round(value),
    });
  }
  return rows;
}

function drawdownSeries(
  equity: { time: string; value: number }[],
): { time: string; value: number }[] {
  let peak = -Infinity;
  return equity.map((point) => {
    peak = Math.max(peak, point.value);
    return { time: point.time, value: (point.value - peak) / peak };
  });
}

const IS_EQUITY = series(36, 100000, 0.012, 2019);
const HO_EQUITY = series(12, IS_EQUITY[IS_EQUITY.length - 1].value, 0.009, 2022);

const A = {
  mgr: "Research Manager",
  mkt: "Market Agent",
  paper: "Paper Agent",
  data: "Data Agent",
  feat: "Feature Agent",
  model: "Modeling Agent",
  back: "Backtest Agent",
  risk: "Risk Auditor",
  report: "Report Agent",
};

type Step = { at: number; event: NormalizedEvent };

function script(): Step[] {
  const s: Step[] = [];
  const add = (at: number, event: NormalizedEvent) => s.push({ at, event });

  add(0, ev("session.status", { status: "running" }));

  // Manager comes up and greets.
  add(150, ev("node.add", { threadId: "mgr", agentName: A.mgr }));
  add(200, ev("node.status", { threadId: "mgr", status: "running" }));
  add(250, ev("cost.add", { threadId: "mgr", ...usage() }));
  add(
    450,
    ev("agent.text", {
      text: "Hello 👋 — running a demo on the S&P 500. Spinning up the research team. (No backend connected, so this is simulated data.)",
    }),
  );

  // Fan-out to the parallel idea agents.
  add(800, ev("node.add", { threadId: "mkt", agentName: A.mkt }));
  add(820, ev("node.add", { threadId: "paper", agentName: A.paper }));
  add(900, ev("edge.animate", { fromThreadId: "mgr", toThreadId: "mkt", direction: "delegate", content: "Generate ideas" }));
  add(960, ev("edge.animate", { fromThreadId: "mgr", toThreadId: "paper", direction: "delegate", content: "Find hypotheses" }));
  add(1000, ev("node.status", { threadId: "mkt", status: "running" }));
  add(1020, ev("node.status", { threadId: "paper", status: "running" }));
  add(1100, ev("agent.thinking", { threadId: "mkt", text: "Scanning momentum & regime signals across sectors…" }));
  add(1150, ev("agent.thinking", { threadId: "paper", text: "Reading time-series momentum literature (Moskowitz et al.)…" }));
  add(1300, ev("cost.add", { threadId: "mkt", ...usage() }));
  add(1320, ev("cost.add", { threadId: "paper", ...usage() }));
  add(1700, ev("edge.animate", { fromThreadId: "mkt", toThreadId: "mgr", direction: "result", content: "3 candidate ideas" }));
  add(1760, ev("edge.animate", { fromThreadId: "paper", toThreadId: "mgr", direction: "result", content: "2 hypotheses" }));
  add(1820, ev("node.status", { threadId: "mkt", status: "idle" }));
  add(1840, ev("node.status", { threadId: "paper", status: "idle" }));

  // Dependent pipeline.
  add(2050, ev("node.add", { threadId: "data", agentName: A.data }));
  add(2080, ev("edge.animate", { fromThreadId: "mgr", toThreadId: "data", direction: "delegate", content: "Pull PIT data" }));
  add(2120, ev("node.status", { threadId: "data", status: "running" }));
  add(2180, ev("agent.thinking", { threadId: "data", text: "Pulling survivorship-free history + FRED vintages…" }));
  add(2250, ev("cost.add", { threadId: "data", ...usage() }));
  add(2500, ev("node.add", { threadId: "feat", agentName: A.feat }));
  add(2540, ev("artifact.write", { threadId: "data", toThreadId: "feat", label: "Wrote features.parquet", artifact: { path: "/workspace/features.parquet", name: "features.parquet", kind: "features" } }));
  add(2580, ev("node.status", { threadId: "data", status: "idle" }));
  add(2620, ev("artifact.write", { threadId: "data", toThreadId: "mgr", label: "data manifest", artifact: { path: "/workspace/data_manifest.json", name: "data_manifest.json", kind: "manifest" } }));
  add(2700, ev("node.status", { threadId: "feat", status: "running" }));
  add(2760, ev("agent.thinking", { threadId: "feat", text: "Building features on train/validation only (holdout sealed)…" }));
  add(2820, ev("cost.add", { threadId: "feat", ...usage() }));

  add(3050, ev("node.add", { threadId: "model", agentName: A.model }));
  add(3090, ev("artifact.write", { threadId: "feat", toThreadId: "model", label: "features_enriched.parquet", artifact: { path: "/workspace/features_enriched.parquet", name: "features_enriched.parquet", kind: "features" } }));
  add(3120, ev("node.status", { threadId: "feat", status: "idle" }));
  add(3180, ev("node.status", { threadId: "model", status: "running" }));
  add(3240, ev("agent.thinking", { threadId: "model", text: "Authoring algo.py to the contract; validating before compile…" }));
  add(3300, ev("cost.add", { threadId: "model", ...usage() }));
  add(3360, ev("provenance.add", { citations: [
    {
      text: "Deep momentum networks learn trend estimation and position sizing directly against a Sharpe objective.",
      source: "https://arxiv.org/abs/1904.04912",
      citation: "Lim, Zohren & Roberts (2019). Enhancing Time Series Momentum Strategies Using Deep Neural Networks. arXiv:1904.04912",
      corpus: "papers",
      score: 0.91,
      metadata: {
        provider: "arxiv",
        title: "Enhancing Time Series Momentum Strategies Using Deep Neural Networks",
        arxiv_id: "1904.04912",
        source_url: "https://arxiv.org/abs/1904.04912",
        pdf_url: "https://arxiv.org/pdf/1904.04912",
        tags: ["arxiv", "demo", "momentum", "machine-learning"],
      },
    },
    {
      text: "Volatility scaling improves momentum Sharpe and tail behaviour.",
      source: "Barroso & Santa-Clara (2015)",
      citation: "JFE 116(1)",
      corpus: "papers",
      score: 0.86,
    },
  ] }));

  add(3650, ev("node.add", { threadId: "back", agentName: A.back }));
  add(3690, ev("artifact.write", { threadId: "model", toThreadId: "back", label: "algo.py", artifact: { path: "/workspace/algo.py", name: "algo.py", kind: "algo" } }));
  add(3720, ev("node.status", { threadId: "model", status: "idle" }));
  add(3780, ev("node.status", { threadId: "back", status: "running" }));
  add(3840, ev("node.badge", { threadId: "back", label: "Running QC backtest" }));
  add(3900, ev("agent.thinking", { threadId: "back", text: "Compiling on QuantConnect; evaluating sealed holdout once…" }));
  add(3960, ev("cost.add", { threadId: "back", ...usage() }));

  // Backtest results.
  add(4300, ev("backtest.update", { result: {
    project_id: "QC-1842203",
    backtest_id: "bt_9f3a21",
    strategy: "Vol-scaled cross-sectional momentum · S&P 500",
    segments: {
      in_sample: {
        start: "2019-01", end: "2021-12",
        metrics: { sharpe: 1.42, max_drawdown: 0.166, total_return: 0.71, win_rate: 0.57 },
        equity_curve: IS_EQUITY,
        drawdown: drawdownSeries(IS_EQUITY),
      },
      holdout: {
        start: "2022-01", end: "2022-12",
        metrics: { sharpe: 1.11, max_drawdown: 0.231, total_return: 0.18, win_rate: 0.54 },
        equity_curve: HO_EQUITY,
        drawdown: drawdownSeries(HO_EQUITY),
      },
    },
  } }));

  // Ledger entries (data-snooping accounting).
  add(4400, ev("ledger.entry", { entry: { ts: new Date().toISOString(), variant_id: "v1-baseline", kind: "iteration", params: { lookback: 126, vol_target: 0.1 }, in_sample_sharpe: 1.28, holdout_sharpe: 0.74, trials_to_date: 1, deflated_sharpe_ratio: 0.31, path: "/workspace/variants/v1.json" } }));
  add(4460, ev("ledger.entry", { entry: { ts: new Date().toISOString(), variant_id: "v2-volscaled", kind: "iteration", params: { lookback: 252, vol_target: 0.12 }, in_sample_sharpe: 1.42, holdout_sharpe: 1.11, trials_to_date: 2, deflated_sharpe_ratio: 0.58, path: "/workspace/variants/v2.json" } }));

  // Risk audit.
  add(4600, ev("node.add", { threadId: "risk", agentName: A.risk }));
  add(4640, ev("artifact.write", { threadId: "back", toThreadId: "risk", label: "results.json", artifact: { path: "/workspace/results.json", name: "results.json", kind: "results" } }));
  add(4680, ev("node.status", { threadId: "back", status: "idle" }));
  add(4740, ev("node.status", { threadId: "risk", status: "running" }));
  add(4800, ev("agent.thinking", { threadId: "risk", text: "Hunting for look-ahead, survivorship leaks, label leakage…" }));
  add(4860, ev("cost.add", { threadId: "risk", ...usage() }));

  // Rubric grading.
  add(4600, ev("rubric.start", { iteration: 2, criteria: [
    { id: "holdout_sharpe", label: "Out-of-sample performance", condition: "Holdout Sharpe > 1.0", status: "running" },
    { id: "is_oos_gap", label: "Overfit guard", condition: "|IS - OOS Sharpe| < 0.5", status: "running" },
    { id: "look_ahead", label: "Look-ahead audit", condition: "Zero look-ahead findings", status: "running" },
    { id: "deflated_sharpe", label: "Multiple-testing correction", condition: "Deflated Sharpe > 0", status: "running" },
    { id: "max_drawdown", label: "Tail risk", condition: "Max drawdown < 25%", status: "running" },
  ] }));

  add(5100, ev("artifact.write", { threadId: "risk", toThreadId: "mgr", label: "audit.json", artifact: { path: "/workspace/audit.json", name: "audit.json", kind: "audit" } }));
  add(5160, ev("node.status", { threadId: "risk", status: "idle" }));

  add(5300, ev("rubric.end", { iteration: 2, result: "fail", explanation: "Passed 4 of 5 gates. Holdout drawdown of 23.1% sits just under the 25% limit and is flagged for review.", criteria: [
    { id: "holdout_sharpe", label: "Out-of-sample performance", condition: "Holdout Sharpe > 1.0", status: "pass", explanation: "Holdout Sharpe 1.11." },
    { id: "is_oos_gap", label: "Overfit guard", condition: "|IS - OOS Sharpe| < 0.5", status: "pass", explanation: "Gap 0.31." },
    { id: "look_ahead", label: "Look-ahead audit", condition: "Zero look-ahead findings", status: "pass", explanation: "No look-ahead found." },
    { id: "deflated_sharpe", label: "Multiple-testing correction", condition: "Deflated Sharpe > 0", status: "pass", explanation: "DSR 0.58 across 2 trials." },
    { id: "max_drawdown", label: "Tail risk", condition: "Max drawdown < 25%", status: "fail", explanation: "Holdout drawdown 23.1% near the limit — flagged." },
  ] }));

  // Report + wrap-up.
  add(5600, ev("node.add", { threadId: "report", agentName: A.report }));
  add(5640, ev("node.status", { threadId: "report", status: "running" }));
  add(5680, ev("artifact.write", { threadId: "report", toThreadId: "mgr", label: "report.pdf", artifact: { path: "/mnt/session/outputs/report.pdf", name: "report.pdf", kind: "report" } }));
  add(5760, ev("cost.add", { threadId: "report", ...usage() }));
  add(5860, ev("node.status", { threadId: "report", status: "idle" }));
  add(5900, ev("node.status", { threadId: "mgr", status: "idle" }));
  add(
    6000,
    ev("agent.text", {
      text: "Demo run complete. The vol-scaled momentum strategy passed 4 of 5 gates — tail risk (23.1% holdout drawdown) is flagged. See the Agents, Results, and Insights tabs to explore the run.",
    }),
  );
  add(6100, ev("session.status", { status: "completed" }));

  return s;
}

let timers: number[] = [];

export function cancelDemo(): void {
  timers.forEach((t) => window.clearTimeout(t));
  timers = [];
}

export function runDemoSession(emit: Emit): void {
  cancelDemo();
  for (const step of script()) {
    timers.push(window.setTimeout(() => emit(step.event), step.at));
  }
}

export function runDemoReply(emit: Emit, message: string): void {
  const trimmed = message.trim();
  const reply = /hello|hi|hey/i.test(trimmed)
    ? "Hello! 👋 Demo mode is active — connect the orchestrator for a real run."
    : `Got it — "${trimmed.slice(0, 80)}". In demo mode I'll just echo; wire up the backend for a real research loop.`;
  timers.push(window.setTimeout(() => emit(ev("agent.text", { text: reply })), 400));
}
