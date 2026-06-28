import { Handle, Position, type NodeProps } from "reactflow";
import type { ThreadState } from "../store/sessionStore";

export function AgentNode({ data }: NodeProps<ThreadState>) {
  return (
    <div className={`agent-node agent-node--${data.status}`}>
      <Handle type="target" position={Position.Left} />
      <div className="agent-node__top">
        <span className="agent-node__status" />
        <span className="agent-node__name">{data.agentName}</span>
      </div>
      <div className="agent-node__meta">{data.status}</div>
      {data.badge ? <div className="agent-node__badge">{data.badge}</div> : null}
      {data.thinking ? <div className="agent-node__thinking">thinking</div> : null}
      {data.tokens > 0 ? <div className="agent-node__tokens">{data.tokens} tokens</div> : null}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
