import { useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  type ReactFlowInstance,
} from "reactflow";
import { AgentNode } from "../components/AgentNode";
import { DelegationEdge } from "../components/DelegationEdge";
import {
  useSessionStore,
  type ArtifactState,
  type ThreadState,
} from "../store/sessionStore";

const nodeTypes = { agent: AgentNode };
const edgeTypes = { delegation: DelegationEdge };

export function AgentGraphCanvas() {
  const threads = useSessionStore((state) => Object.values(state.threads));
  const graphEdges = useSessionStore((state) => state.edges);
  const artifacts = useSessionStore((state) => Object.values(state.artifacts));
  const now = useNow();
  const flowRef = useRef<ReactFlowInstance | null>(null);

  // Re-fit the viewport whenever an agent is added so the whole graph stays
  // framed (nodes stream in over time and aren't measured at first fit).
  useEffect(() => {
    const timer = window.setTimeout(() => {
      flowRef.current?.fitView({ padding: 0.18, duration: 350 });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [threads.length]);

  const nodes: Node<ThreadState>[] = useMemo(
    () =>
      threads.map((thread, index) => ({
        id: thread.threadId,
        type: "agent",
        position: positionFor(thread, index),
        data: thread,
      })),
    [threads],
  );

  const edges: Edge[] = useMemo(() => {
    const artifactLookup = new Map(
      artifacts.map((artifact) => [artifact.id, artifact]),
    );
    return graphEdges.map((edge) => ({
      id: edge.id,
      source: edge.fromThreadId,
      target: edge.toThreadId,
      type: "delegation",
      animated: edge.animatingUntil > now,
      data: {
        direction: edge.direction,
        label: edge.label,
        artifacts: (edge.artifactIds ?? [])
          .map((id) => artifactLookup.get(id))
          .filter((artifact): artifact is ArtifactState =>
            Boolean(artifact && artifact.animatingUntil > now),
          ),
      },
    }));
  }, [artifacts, graphEdges, now]);

  const orderedArtifacts = useMemo(
    () => [...artifacts].sort(compareArtifacts),
    [artifacts],
  );

  return (
    <div className="canvas-shell" data-testid="agent-graph-canvas">
      {nodes.length === 0 ? (
        <div className="canvas-empty">Waiting for session events</div>
      ) : null}
      {orderedArtifacts.length > 0 ? (
        <div className="artifact-rail" aria-label="File bus artifacts">
          {orderedArtifacts.map((artifact) => (
            <div
              key={artifact.id}
              className={`artifact-pill artifact-pill--${artifact.kind}`}
            >
              <span>{artifact.name}</span>
              <code>{artifact.path}</code>
            </div>
          ))}
        </div>
      ) : null}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={(instance) => {
          flowRef.current = instance;
        }}
        fitView
        minZoom={0.3}
        maxZoom={1.6}
      >
        <Background color="var(--border)" gap={22} size={1} />
        <Controls className="flow-controls" showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

// Left→right layered layout that mirrors the workflow: the Manager fans out to
// the parallel agents, then the dependent pipeline runs across one row.
const LAYOUT: Array<[RegExp, { x: number; y: number }]> = [
  [/manager/i, { x: 0, y: 250 }],
  [/market/i, { x: 380, y: 20 }],
  [/paper/i, { x: 380, y: 260 }],
  [/data/i, { x: 380, y: 500 }],
  [/feature/i, { x: 740, y: 500 }],
  [/model/i, { x: 1100, y: 500 }],
  [/backtest/i, { x: 1460, y: 500 }],
  [/risk|audit/i, { x: 1820, y: 500 }],
  [/report/i, { x: 1820, y: 740 }],
];

function positionFor(thread: ThreadState, index: number) {
  for (const [pattern, position] of LAYOUT) {
    if (pattern.test(thread.agentName)) return position;
  }
  const column = index % 4;
  const row = Math.floor(index / 4);
  return { x: column * 360, y: row * 240 };
}

function useNow() {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 400);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

function compareArtifacts(a: ArtifactState, b: ArtifactState) {
  const order: Record<ArtifactState["kind"], number> = {
    features: 1,
    manifest: 2,
    algo: 3,
    results: 4,
    audit: 5,
    report: 6,
    artifact: 7,
  };
  return order[a.kind] - order[b.kind] || a.name.localeCompare(b.name);
}
