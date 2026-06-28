import { useEffect, useMemo, useState } from "react";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  useSessionStore,
  type BacktestSegment,
  type BacktestState,
} from "../store/sessionStore";

type BacktestResultsProps = {
  sessionId: string | null;
};

type ChartRow = {
  time: string;
  in_sample?: number;
  holdout?: number;
};

export function BacktestResults({ sessionId }: BacktestResultsProps) {
  const backtest = useSessionStore((state) => state.backtest);
  const setBacktestResults = useSessionStore(
    (state) => state.setBacktestResults,
  );
  const [status, setStatus] = useState<
    "idle" | "loading" | "ready" | "missing" | "error"
  >("idle");

  useEffect(() => {
    if (!sessionId) {
      setStatus("idle");
      return undefined;
    }

    let active = true;
    const load = async () => {
      setStatus((current) => (current === "ready" ? current : "loading"));
      try {
        const response = await fetch(`/api/sessions/${sessionId}/results`);
        if (response.status === 404) {
          if (active) setStatus("missing");
          return;
        }
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const body = (await response.json()) as { results: BacktestState };
        if (active) {
          setBacktestResults(body.results);
          setStatus("ready");
        }
      } catch {
        if (active) setStatus("error");
      }
    };

    void load();
    const timer = window.setInterval(load, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [sessionId, setBacktestResults]);

  const segments = backtest?.segments ?? {};
  const equityRows = useMemo(
    () => mergeSeries(segments, "equity_curve"),
    [segments],
  );
  const drawdownRows = useMemo(
    () => mergeSeries(segments, "drawdown"),
    [segments],
  );
  const hasStructuredResults = equityRows.length > 0 || drawdownRows.length > 0;
  const hasRawUpdates = Boolean(
    backtest?.rawUpdates && Object.keys(backtest.rawUpdates).length > 0,
  );

  return (
    <Card className="results-panel" aria-label="Backtest results">
      <CardHeader className="results-panel__header">
        <div>
          <CardTitle className="panel-title">Backtest Results</CardTitle>
          <CardDescription className="panel-subtitle">
            {backtest?.strategy ?? statusLabel(status, hasRawUpdates)}
          </CardDescription>
        </div>
        <CardAction className="results-panel__ids">
          {backtest?.project_id ? (
            <Badge variant="outline">{backtest.project_id}</Badge>
          ) : null}
          {backtest?.backtest_id ? (
            <Badge variant="outline">{backtest.backtest_id}</Badge>
          ) : null}
        </CardAction>
      </CardHeader>

      {hasStructuredResults ? (
        <CardContent className="results-panel__content">
          <ScrollArea className="results-panel__body">
            <div className="results-panel__inner">
              <div className="metric-grid">
                <Metric
                  label="IS Sharpe"
                  value={metric(segments.in_sample, "sharpe")}
                />
                <Metric
                  label="HO Sharpe"
                  value={metric(segments.holdout, "sharpe")}
                />
                <Metric
                  label="IS Drawdown"
                  value={metric(segments.in_sample, "max_drawdown")}
                  percent
                />
                <Metric
                  label="HO Drawdown"
                  value={metric(segments.holdout, "max_drawdown")}
                  percent
                />
              </div>

              <div className="chart-grid">
                <Chart
                  title="Equity"
                  rows={equityRows}
                  valueFormatter={formatMoney}
                />
                <Chart
                  title="Drawdown"
                  rows={drawdownRows}
                  valueFormatter={formatPercent}
                />
              </div>
            </div>
          </ScrollArea>
        </CardContent>
      ) : (
        <CardContent className="results-empty">
          {status === "loading" ? (
            <div className="results-skeleton">
              <Skeleton className="h-7 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : hasRawUpdates ? (
            "QC backtest responses received. Waiting for structured results.json."
          ) : (
            "No backtest results yet."
          )}
        </CardContent>
      )}
    </Card>
  );
}

function Metric({
  label,
  value,
  percent = false,
}: {
  label: string;
  value: number | null;
  percent?: boolean;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>
        {value === null
          ? "--"
          : percent
            ? formatPercent(value)
            : value.toFixed(2)}
      </strong>
    </div>
  );
}

function Chart({
  title,
  rows,
  valueFormatter,
}: {
  title: string;
  rows: ChartRow[];
  valueFormatter: (value: number) => string;
}) {
  return (
    <div className="chart-surface">
      <div className="chart-title">{title}</div>
      <ResponsiveContainer width="100%" height={190}>
        <LineChart
          data={rows}
          margin={{ top: 8, right: 10, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="time"
            minTickGap={26}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickFormatter={valueFormatter}
            width={58}
          />
          <Tooltip
            formatter={(value) => valueFormatter(Number(value))}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              color: "var(--popover-foreground)",
            }}
            labelStyle={{ color: "var(--foreground)" }}
          />
          <Legend
            wrapperStyle={{ color: "var(--muted-foreground)", fontSize: 12 }}
          />
          <Line
            type="monotone"
            dataKey="in_sample"
            name="In-sample"
            stroke="var(--chart-1)"
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="holdout"
            name="Holdout"
            stroke="var(--chart-2)"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function mergeSeries(
  segments: Record<string, BacktestSegment>,
  key: "equity_curve" | "drawdown",
): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  for (const segmentName of ["in_sample", "holdout"] as const) {
    const points = segments[segmentName]?.[key] ?? [];
    for (const point of points) {
      if (!point.time || typeof point.value !== "number") continue;
      const row = rows.get(point.time) ?? { time: point.time };
      row[segmentName] = point.value;
      rows.set(point.time, row);
    }
  }
  return Array.from(rows.values()).sort((a, b) => a.time.localeCompare(b.time));
}

function metric(
  segment: BacktestSegment | undefined,
  key: string,
): number | null {
  const value = segment?.metrics?.[key];
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const cleaned = value.replace("%", "");
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatMoney(value: number): string {
  if (Math.abs(value) >= 1000) {
    return `$${Math.round(value).toLocaleString()}`;
  }
  return `$${value.toFixed(0)}`;
}

function formatPercent(value: number): string {
  const scaled = Math.abs(value) <= 1 ? value * 100 : value;
  return `${scaled.toFixed(1)}%`;
}

function statusLabel(status: string, hasRawUpdates: boolean): string {
  if (hasRawUpdates) return "QC responses received";
  if (status === "loading") return "Checking session outputs";
  if (status === "error") return "Results bridge unavailable";
  return "Waiting for results.json";
}
