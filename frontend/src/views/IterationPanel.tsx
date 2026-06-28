import { useSessionStore, type CriterionStatus } from "../store/sessionStore";

export function IterationPanel() {
  const outcome = useSessionStore((state) => state.outcome);

  return (
    <section className="phase-panel" data-testid="iteration-panel" aria-label="Iteration rubric">
      <header className="phase-panel__header">
        <div>
          <div className="panel-title">Iteration</div>
          <div className="panel-subtitle">
            {outcome.running ? "grader running" : outcome.result ?? "waiting"}
          </div>
        </div>
        <div className="iteration-count">#{outcome.iteration || 0}</div>
      </header>
      <div className="rubric-list">
        {outcome.criteria.map((criterion) => (
          <div key={criterion.id} className="rubric-row">
            <span className={`rubric-status rubric-status--${criterion.status}`}>
              {statusLabel(criterion.status)}
            </span>
            <div className="rubric-main">
              <strong>{criterion.label}</strong>
              <span>{criterion.condition}</span>
              {criterion.explanation ? <p>{criterion.explanation}</p> : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function statusLabel(status: CriterionStatus): string {
  if (status === "pass") return "Pass";
  if (status === "fail") return "Fail";
  if (status === "running") return "Run";
  return "Open";
}
