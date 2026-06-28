import { useEffect, useState } from "react";
import { DownloadIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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
    <Card
      className="phase-panel report-panel"
      data-testid="report-deliverable"
      aria-label="Report"
    >
      <CardHeader className="phase-panel__header">
        <div>
          <CardTitle className="panel-title">Report</CardTitle>
          <CardDescription className="panel-subtitle">
            {subtitle(status, file)}
          </CardDescription>
        </div>
        {file ? (
          <CardAction>
            <Button asChild size="sm">
              <a href={file.downloadUrl}>
                <DownloadIcon data-icon="inline-start" />
                Download
              </a>
            </Button>
          </CardAction>
        ) : null}
      </CardHeader>
      <CardContent className="report-body">
        {file ? (
          <>
            <strong>{file.filename}</strong>
            <span>
              {file.createdAt
                ? `Indexed ${formatDate(file.createdAt)}`
                : "Indexed by Files API"}
            </span>
            {typeof file.sizeBytes === "number" ? (
              <Badge variant="outline">{formatBytes(file.sizeBytes)}</Badge>
            ) : null}
          </>
        ) : (
          <div className="phase-empty">{emptyText(status)}</div>
        )}
      </CardContent>
    </Card>
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
