// AgentNode — custom React Flow node for one agent thread.
// Renders: agent name; a status ring (idle/working pulse from node.status); a current-action badge
// (node.badge, e.g. "compiling on QC"); a "thinking…" shimmer (agent.thinking); a token/cost meter
// (cost.add from span.model_request_end). STATUS: scaffold.
// import { Handle, Position, NodeProps } from "reactflow";
export function AgentNode(/* props: NodeProps */) {
  return <div className="agent-node">AgentNode (scaffold)</div>;
}
