import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardFooter,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useSessionStore, type CriterionStatus } from "../store/sessionStore";

export function IterationPanel() {
  const outcome = useSessionStore((state) => state.outcome);
  const completed = outcome.criteria.filter(
    (criterion) => criterion.status === "pass",
  ).length;
  const progress = outcome.criteria.length
    ? (completed / outcome.criteria.length) * 100
    : 0;

  return (
    <Card
      className="phase-panel"
      data-testid="iteration-panel"
      aria-label="Iteration rubric"
    >
      <CardHeader className="phase-panel__header">
        <div>
          <CardTitle className="panel-title">Iteration</CardTitle>
          <CardDescription className="panel-subtitle">
            {outcome.running ? "grader running" : (outcome.result ?? "waiting")}
          </CardDescription>
        </div>
        <CardAction>
          <Badge variant={outcome.running ? "default" : "secondary"}>
            #{outcome.iteration || 0}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="phase-panel__content">
        <ScrollArea className="rubric-list">
          <div className="rubric-list__inner">
            {outcome.criteria.map((criterion) => (
              <div key={criterion.id} className="rubric-row">
                <Badge
                  className={`rubric-status rubric-status--${criterion.status}`}
                  variant={variantFor(criterion.status)}
                >
                  {statusLabel(criterion.status)}
                </Badge>
                <div className="rubric-main">
                  <strong>{criterion.label}</strong>
                  <span>{criterion.condition}</span>
                  {criterion.explanation ? (
                    <p>{criterion.explanation}</p>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
      <CardFooter className="phase-panel__footer">
        <Progress value={progress} aria-label="Rubric pass progress" />
      </CardFooter>
    </Card>
  );
}

function variantFor(
  status: CriterionStatus,
): "default" | "secondary" | "destructive" | "outline" {
  if (status === "pass") return "default";
  if (status === "fail") return "destructive";
  if (status === "running") return "secondary";
  return "outline";
}

function statusLabel(status: CriterionStatus): string {
  if (status === "pass") return "Pass";
  if (status === "fail") return "Fail";
  if (status === "running") return "Run";
  return "Open";
}
