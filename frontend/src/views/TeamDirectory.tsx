import {
  ActivityIcon,
  BookOpenIcon,
  CodeIcon,
  DatabaseIcon,
  FileTextIcon,
  NetworkIcon,
  ShieldCheckIcon,
  SlidersIcon,
  TrendingUpIcon,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { WorkflowFlowchart } from "./WorkflowFlowchart";

type Agent = {
  name: string;
  model: string;
  icon: LucideIcon;
  guardrail: string;
  role: string;
  sources: string[];
};

type Phase = {
  id: string;
  title: string;
  caption: string;
  agents: Agent[];
};

const PHASES: Phase[] = [
  {
    id: "coordinator",
    title: "Coordinator",
    caption: "Receives your goal and runs the loop — never does the work itself.",
    agents: [
      {
        name: "Research Manager",
        model: "Opus 4.8",
        icon: NetworkIcon,
        guardrail: "Orchestrator",
        role: "Breaks your request into tasks, delegates to one specialist at a time, waits for each result, and grades the strategy against the 5-gate rubric — looping until it passes or hits the iteration cap.",
        sources: ["Knowledge base"],
      },
    ],
  },
  {
    id: "ideation",
    title: "Ideation",
    caption: "Generates candidate ideas. Walled off from the backtest so no live context can leak in.",
    agents: [
      {
        name: "Market Agent",
        model: "Sonnet 4.6",
        icon: TrendingUpIcon,
        guardrail: "Idea-only",
        role: "Surfaces strategy ideas and current market context to seed research. Its output frames ideas only — it never feeds a backtest.",
        sources: ["Web search", "FRED · macro", "GDELT · events"],
      },
      {
        name: "Paper Agent",
        model: "Haiku 4.5",
        icon: BookOpenIcon,
        guardrail: "Idea-only",
        role: "Turns academic literature into concrete, testable hypotheses, always citing its sources for the provenance view.",
        sources: ["Knowledge base", "arXiv", "SSRN", "Web"],
      },
    ],
  },
  {
    id: "build",
    title: "Data & Build",
    caption: "Point-in-time safe: only ever uses data as it was known at the time. No web access.",
    agents: [
      {
        name: "Data Agent",
        model: "Haiku 4.5",
        icon: DatabaseIcon,
        guardrail: "Point-in-time",
        role: "Pulls survivorship-bias-free, as-it-was-known data and records the source and as-of timestamp for every pull.",
        sources: ["QuantConnect", "FRED / ALFRED", "EDGAR · filings", "GDELT"],
      },
      {
        name: "Feature Agent",
        model: "Sonnet 4.6",
        icon: SlidersIcon,
        guardrail: "Point-in-time",
        role: "Builds and validates the predictive signals in QuantConnect research — reading only the train/validation splits, never the sealed holdout.",
        sources: ["QuantConnect · QuantBook", "Knowledge base"],
      },
      {
        name: "Modeling Agent",
        model: "Opus 4.8",
        icon: CodeIcon,
        guardrail: "Point-in-time",
        role: "Writes the actual strategy as a QuantConnect algorithm to the authoring contract, and self-validates it before compiling.",
        sources: ["QuantConnect", "Knowledge base"],
      },
    ],
  },
  {
    id: "validation",
    title: "Validation",
    caption: "Runs the simulation and independently checks the work for bias.",
    agents: [
      {
        name: "Backtest Agent",
        model: "Opus 4.8",
        icon: ActivityIcon,
        guardrail: "No live trading",
        role: "Runs the QuantConnect backtest and evaluates the sealed holdout exactly once — recording both in-sample and holdout performance.",
        sources: ["QuantConnect · backtests"],
      },
      {
        name: "Risk Auditor",
        model: "Opus 4.8",
        icon: ShieldCheckIcon,
        guardrail: "Independent",
        role: "A fresh, skeptical reviewer that hunts for look-ahead, survivorship leaks, and data-snooping — and did not design the strategy it audits.",
        sources: ["Knowledge base · bias patterns"],
      },
    ],
  },
  {
    id: "output",
    title: "Output",
    caption: "Turns the run's artifacts into a faithful, readable deliverable.",
    agents: [
      {
        name: "Report Agent",
        model: "Sonnet 4.6",
        icon: FileTextIcon,
        guardrail: "Read-only",
        role: "Writes the final research report — holdout vs in-sample honestly, variants tried, and any look-ahead findings surfaced.",
        sources: ["Run artifacts"],
      },
    ],
  },
];

export function TeamDirectory() {
  return (
    <div className="team-page">
      <div className="team-intro">
        <h1 className="team-intro__title">The research team</h1>
        <p className="team-intro__sub">
          Nine specialized agents coordinated by a single manager. Each has one
          job and a defined set of sources it is allowed to consult — the
          guardrails are what keep a backtest honest.
        </p>
      </div>

      <div className="team-flow">
        <div className="team-flow__head">
          <h2 className="team-section__title">Workflow</h2>
          <p className="team-section__caption">
            How a query moves through the team — looping on the rubric until it
            passes.
          </p>
        </div>
        <WorkflowFlowchart />
      </div>

      {PHASES.map((phase) => (
        <section key={phase.id} className="team-section">
          <div className="team-section__head">
            <h2 className="team-section__title">{phase.title}</h2>
            <p className="team-section__caption">{phase.caption}</p>
          </div>
          <div className="team-grid">
            {phase.agents.map((agent) => (
              <article key={agent.name} className="team-card">
                <div className="team-card__head">
                  <span className="team-card__icon">
                    <agent.icon />
                  </span>
                  <div className="team-card__title">
                    <span className="team-card__name">{agent.name}</span>
                    <span className="team-card__model">{agent.model}</span>
                  </div>
                  <Badge variant="outline" className="team-card__guardrail">
                    {agent.guardrail}
                  </Badge>
                </div>
                <p className="team-card__role">{agent.role}</p>
                <div className="team-card__sources">
                  <span className="team-card__sources-label">Consults</span>
                  <div className="team-card__source-list">
                    {agent.sources.map((source) => (
                      <Badge
                        key={source}
                        variant="secondary"
                        className="team-source"
                      >
                        {source}
                      </Badge>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
