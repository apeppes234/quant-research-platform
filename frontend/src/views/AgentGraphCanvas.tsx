// AgentGraphCanvas — the live topology (React Flow). The hero view.
// Bindings (docs/09): node.add -> add node; node.status -> pulse/settle; edge.animate -> animate edge;
// node.badge -> show current action. Custom node = AgentNode, custom edge = DelegationEdge.
// STATUS: scaffold.
// import ReactFlow, { Background, Controls } from "reactflow";
// import "reactflow/dist/style.css";
// import { AgentNode } from "../components/AgentNode";
// import { DelegationEdge } from "../components/DelegationEdge";

export function AgentGraphCanvas() {
  // const { nodes, edges } = useSessionStore(selectGraph);
  // return <ReactFlow nodes={nodes} edges={edges} nodeTypes={{agent: AgentNode}} edgeTypes={{delegation: DelegationEdge}}><Background/><Controls/></ReactFlow>;
  return <div data-testid="agent-graph-canvas">AgentGraphCanvas (scaffold)</div>;
}
