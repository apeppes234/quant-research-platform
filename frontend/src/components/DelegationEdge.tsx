import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "reactflow";
import type { ArtifactState, EdgeDirection } from "../store/sessionStore";

type DelegationEdgeData = {
  direction?: EdgeDirection;
  label?: string;
  artifacts?: ArtifactState[];
};

export function DelegationEdge(props: EdgeProps<DelegationEdgeData>) {
  const [path, labelX, labelY] = getBezierPath(props);
  const direction = props.data?.direction ?? "delegate";
  const artifacts = props.data?.artifacts ?? [];

  return (
    <>
      <BaseEdge
        path={path}
        markerEnd={props.markerEnd}
        style={{
          stroke: edgeColor(direction),
          strokeWidth: 2,
          strokeDasharray: props.animated ? "6 6" : undefined,
        }}
      />
      {artifacts.map((artifact, index) => (
        <g
          key={`${artifact.id}:${index}`}
          className={`artifact-chip-svg artifact-chip-svg--${artifact.kind}`}
        >
          <rect
            x={-chipWidth(artifact.name) / 2}
            y={-12}
            width={chipWidth(artifact.name)}
            height={24}
            rx={6}
          />
          <text textAnchor="middle" dominantBaseline="central">
            {trimArtifactName(artifact.name)}
          </text>
          <animateMotion
            begin={`${index * 0.18}s`}
            dur="2.6s"
            fill="freeze"
            path={path}
            repeatCount="1"
          />
        </g>
      ))}
      {props.data?.label ? (
        <EdgeLabelRenderer>
          <div
            className="delegation-edge__label"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)` }}
          >
            {props.data.label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}

function edgeColor(direction: EdgeDirection): string {
  if (direction === "result") return "#0f9f6e";
  if (direction === "artifact") return "#b54708";
  return "#3485a4";
}

function trimArtifactName(name: string): string {
  return name.length > 18 ? `${name.slice(0, 15)}...` : name;
}

function chipWidth(name: string): number {
  return Math.max(62, Math.min(122, trimArtifactName(name).length * 7 + 20));
}
