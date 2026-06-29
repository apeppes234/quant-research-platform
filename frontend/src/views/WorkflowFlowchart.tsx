import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";

type FlowHandle = {
  id?: string;
  type: "source" | "target";
  position: Position;
};

type FlowData = {
  name: string;
  sub?: string;
  shape?: "terminator" | "process";
  handles: FlowHandle[];
};

function renderHandles(handles: FlowHandle[]) {
  return handles.map((handle, index) => (
    <Handle
      key={handle.id ?? `${handle.type}-${index}`}
      id={handle.id}
      type={handle.type}
      position={handle.position}
      className="fc-handle"
      isConnectable={false}
    />
  ));
}

function BoxNode({ data }: NodeProps<FlowData>) {
  return (
    <div className={`fc-node fc-node--${data.shape ?? "process"}`}>
      {renderHandles(data.handles)}
      <span className="fc-node__name">{data.name}</span>
      {data.sub ? <span className="fc-node__sub">{data.sub}</span> : null}
    </div>
  );
}

function DecisionNode({ data }: NodeProps<FlowData>) {
  return (
    <div className="fc-decision">
      <div className="fc-decision__shape" />
      <span className="fc-decision__label">{data.name}</span>
      {renderHandles(data.handles)}
    </div>
  );
}

const nodeTypes = { box: BoxNode, decision: DecisionNode };

const STACK_X = 450;
const PIPE_Y = 300;
const ROW_B = 488;
const STEP = 200;

const nodes: Node<FlowData>[] = [
  {
    id: "start",
    type: "box",
    position: { x: 20, y: 150 },
    data: {
      name: "Query submitted",
      shape: "terminator",
      handles: [{ type: "source", position: Position.Right }],
    },
  },
  {
    id: "manager",
    type: "box",
    position: { x: 210, y: 144 },
    data: {
      name: "Research Manager",
      sub: "Plans & delegates",
      handles: [
        { type: "target", position: Position.Left },
        { type: "source", position: Position.Right },
      ],
    },
  },
  // Fan-out: parallel agents dispatched by the manager.
  {
    id: "market",
    type: "box",
    position: { x: STACK_X, y: 24 },
    data: {
      name: "Market Agent",
      sub: "Idea generation",
      handles: [{ type: "target", position: Position.Left }],
    },
  },
  {
    id: "paper",
    type: "box",
    position: { x: STACK_X, y: 150 },
    data: {
      name: "Paper Agent",
      sub: "Literature → hypotheses",
      handles: [{ type: "target", position: Position.Left }],
    },
  },
  // Dependent pipeline: each feeds the next.
  {
    id: "data",
    type: "box",
    position: { x: STACK_X, y: PIPE_Y },
    data: {
      name: "Data Agent",
      sub: "Point-in-time data",
      handles: [
        { type: "target", position: Position.Left },
        { type: "source", position: Position.Right },
      ],
    },
  },
  {
    id: "feature",
    type: "box",
    position: { x: STACK_X + STEP, y: PIPE_Y },
    data: {
      name: "Feature Agent",
      sub: "Build features",
      handles: [
        { type: "target", position: Position.Left },
        { type: "source", position: Position.Right },
      ],
    },
  },
  {
    id: "modeling",
    type: "box",
    position: { x: STACK_X + STEP * 2, y: PIPE_Y },
    data: {
      name: "Modeling Agent",
      sub: "Author algo.py",
      handles: [
        { type: "target", position: Position.Left },
        { id: "loop", type: "target", position: Position.Top },
        { type: "source", position: Position.Right },
      ],
    },
  },
  {
    id: "backtest",
    type: "box",
    position: { x: STACK_X + STEP * 3, y: PIPE_Y },
    data: {
      name: "Backtest Agent",
      sub: "Run QC backtest",
      handles: [
        { type: "target", position: Position.Left },
        { type: "source", position: Position.Right },
      ],
    },
  },
  {
    id: "risk",
    type: "box",
    position: { x: STACK_X + STEP * 4, y: PIPE_Y },
    data: {
      name: "Risk Auditor",
      sub: "Audit for bias",
      handles: [
        { type: "target", position: Position.Left },
        { type: "source", position: Position.Right },
      ],
    },
  },
  {
    id: "decision",
    type: "decision",
    position: { x: STACK_X + STEP * 5, y: PIPE_Y - 8 },
    data: {
      name: "Passes 5-gate rubric?",
      handles: [
        { type: "target", position: Position.Left },
        { id: "no", type: "source", position: Position.Top },
        { id: "yes", type: "source", position: Position.Bottom },
      ],
    },
  },
  {
    id: "report",
    type: "box",
    position: { x: STACK_X + STEP * 4 + 70, y: ROW_B },
    data: {
      name: "Report Agent",
      sub: "Write research report",
      handles: [
        { type: "target", position: Position.Right },
        { type: "source", position: Position.Left },
      ],
    },
  },
  {
    id: "deliver",
    type: "box",
    position: { x: STACK_X + STEP * 3, y: ROW_B + 6 },
    data: {
      name: "Deliver results",
      shape: "terminator",
      handles: [{ type: "target", position: Position.Right }],
    },
  },
];

const marker = {
  type: MarkerType.ArrowClosed,
  width: 16,
  height: 16,
  color: "#8b8b8b",
};

const edge = (id: string, source: string, target: string): Edge => ({
  id,
  source,
  target,
  type: "smoothstep",
  markerEnd: marker,
});

const edges: Edge[] = [
  edge("e-start", "start", "manager"),
  // Fan-out — manager dispatches these in parallel.
  edge("e-mkt", "manager", "market"),
  edge("e-paper", "manager", "paper"),
  edge("e-data", "manager", "data"),
  // Dependent pipeline.
  edge("e-feat", "data", "feature"),
  edge("e-model", "feature", "modeling"),
  edge("e-back", "modeling", "backtest"),
  edge("e-risk", "backtest", "risk"),
  edge("e-dec", "risk", "decision"),
  {
    id: "e-yes",
    source: "decision",
    sourceHandle: "yes",
    target: "report",
    type: "smoothstep",
    label: "Yes",
    markerEnd: marker,
  },
  {
    id: "e-no",
    source: "decision",
    sourceHandle: "no",
    target: "modeling",
    targetHandle: "loop",
    type: "smoothstep",
    label: "No · iterate (≤5)",
    markerEnd: marker,
    pathOptions: { offset: 26, borderRadius: 10 },
  },
  edge("e-report", "report", "deliver"),
];

export function WorkflowFlowchart() {
  return (
    <div className="flowchart">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.3}
        maxZoom={1.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
