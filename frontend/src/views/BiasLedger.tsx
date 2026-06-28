import { useMemo } from "react";
import { useSessionStore, type LedgerEntry } from "../store/sessionStore";

const EULER_GAMMA = 0.5772156649015329;

export function BiasLedger() {
  const ledger = useSessionStore((state) => state.ledger);
  const summary = useMemo(() => summarizeLedger(ledger), [ledger]);

  return (
    <section className="phase-panel" data-testid="bias-ledger" aria-label="Bias ledger">
      <header className="phase-panel__header">
        <div>
          <div className="panel-title">Bias Ledger</div>
          <div className="panel-subtitle">{ledger.length} variants logged</div>
        </div>
        <div className={summary.dsr > 0 ? "dsr dsr--pass" : "dsr"}>
          <span>DSR</span>
          <strong>{formatNumber(summary.dsr)}</strong>
        </div>
      </header>

      <div className="ledger-metrics">
        <Metric label="Trials" value={String(summary.trials)} />
        <Metric label="Best OOS" value={formatNumber(summary.bestHoldout)} />
        <Metric label="Avg Gap" value={formatNumber(summary.averageGap)} />
      </div>

      <div className="ledger-list">
        {ledger.length === 0 ? <div className="phase-empty">No variants logged yet.</div> : null}
        {ledger.slice(-5).reverse().map((entry) => (
          <div key={entry.variant_id ?? `${entry.path}:${entry.ts}`} className="ledger-row">
            <div>
              <strong>{entry.variant_id || entry.kind || "variant"}</strong>
              <span>{entry.ts ? new Date(entry.ts).toLocaleString() : "pending timestamp"}</span>
            </div>
            <code>{formatGap(entry)}</code>
          </div>
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="ledger-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function summarizeLedger(entries: LedgerEntry[]) {
  const sharpes = entries
    .map((entry) => entry.holdout_sharpe)
    .filter((value): value is number => typeof value === "number");
  const trials = Math.max(
    entries.length,
    ...entries.map((entry) => entry.trials_to_date ?? 0),
    0
  );
  const explicit = [...entries]
    .reverse()
    .find((entry) => typeof entry.deflated_sharpe_ratio === "number")?.deflated_sharpe_ratio;
  const bestHoldout = sharpes.length ? Math.max(...sharpes) : 0;
  const dsr = explicit ?? computeDeflatedSharpe(sharpes, trials);
  const gaps = entries
    .map((entry) =>
      typeof entry.in_sample_sharpe === "number" && typeof entry.holdout_sharpe === "number"
        ? entry.in_sample_sharpe - entry.holdout_sharpe
        : null
    )
    .filter((value): value is number => value !== null);
  const averageGap = gaps.length ? gaps.reduce((sum, value) => sum + value, 0) / gaps.length : 0;
  return { trials, bestHoldout, dsr, averageGap };
}

function computeDeflatedSharpe(sharpes: number[], trials: number): number {
  if (sharpes.length === 0) return 0;
  const best = Math.max(...sharpes);
  const n = Math.max(trials, sharpes.length, 1);
  if (n <= 1) return best;
  const sigma = standardDeviation(sharpes) || 1;
  const expectedMax =
    sigma *
    ((1 - EULER_GAMMA) * inverseNormal(1 - 1 / n) +
      EULER_GAMMA * inverseNormal(1 - 1 / (n * Math.E)));
  return best - expectedMax;
}

function standardDeviation(values: number[]): number {
  if (values.length < 2) return 0;
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function inverseNormal(p: number): number {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const plow = 0.02425;
  const phigh = 1 - plow;
  if (p <= 0) return Number.NEGATIVE_INFINITY;
  if (p >= 1) return Number.POSITIVE_INFINITY;
  if (p < plow) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > phigh) {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  const q = p - 0.5;
  const r = q * q;
  return (
    (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) *
    q
  ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "--";
  return value.toFixed(2);
}

function formatGap(entry: LedgerEntry): string {
  if (typeof entry.in_sample_sharpe !== "number" || typeof entry.holdout_sharpe !== "number") {
    return "gap --";
  }
  return `gap ${(entry.in_sample_sharpe - entry.holdout_sharpe).toFixed(2)}`;
}
