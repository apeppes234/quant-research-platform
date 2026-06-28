import { useEffect, useState } from "react";

type Props = {
  sessionId: string | null;
};

type ReportFile = {
  id: string;
  filename: string;
  downloadUrl: string;
  createdAt?: string;
  sizeBytes?: number;
  mimeType?: string;
};

type ReportStatus = "idle" | "loading" | "missing" | "ready" | "error";

export function ReportDeliverable({ sessionId }: Props) {
  const [status, setStatus] = useState<ReportStatus>("idle");
  const [file, setFile] = useState<ReportFile | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setStatus("idle");
      setFile(null);
      return undefined;
    }

    let active = true;
    const load = async () => {
      setStatus((current) => (current === "ready" ? current : "loading"));
      try {
        const response = await fetch(`/api/sessions/${sessionId}/report`);
        if (response.status === 404) {
          if (active) setStatus("missing");
          return;
        }
        if (!response.ok) {
          throw new Error(await response.text());
        }
        const body = (await response.json()) as { file: ReportFile };
        if (active) {
          setFile(body.file);
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
  }, [sessionId]);

  return (
    <section className="phase-panel report-panel" data-testid="report-deliverable" aria-label="Report">
      <header className="phase-panel__header">
        <div>
          <div className="panel-title">Report</div>
          <div className="panel-subtitle">{subtitle(status, file)}</div>
        </div>
        {file ? (
          <a className="download-link" href={file.downloadUrl}>
            Download
          </a>
        ) : null}
      </header>
      <div className="report-body">
        {file ? (
          <>
            <strong>{file.filename}</strong>
            <span>{file.createdAt ? `Indexed ${formatDate(file.createdAt)}` : "Indexed by Files API"}</span>
            {typeof file.sizeBytes === "number" ? <code>{formatBytes(file.sizeBytes)}</code> : null}
          </>
        ) : (
          <div className="phase-empty">{emptyText(status)}</div>
        )}
      </div>
    </section>
  );
}

function subtitle(status: ReportStatus, file: ReportFile | null): string {
  if (file) return "PDF ready";
  if (status === "loading") return "Checking outputs";
  if (status === "error") return "Files bridge unavailable";
  return "Waiting for report.pdf";
}

function emptyText(status: ReportStatus): string {
  if (status === "error") return "Could not list session outputs.";
  if (status === "idle") return "Start a session to produce a report.";
  return "Report agent has not published report.pdf yet.";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
