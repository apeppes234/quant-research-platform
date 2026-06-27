// Websocket client to the orchestrator: WS /sessions/{id}/stream.
// Receives normalized events ({kind, id, payload}) and feeds the store, DEDUPING BY event id
// (the orchestrator may replay recent events on reconnect). STATUS: scaffold.

export type NormalizedEvent = { kind: string; id: string; payload: Record<string, unknown> };

export function connect(sessionId: string, onEvent: (e: NormalizedEvent) => void): () => void {
  // const seen = new Set<string>();
  // const ws = new WebSocket(`/ws/sessions/${sessionId}/stream`);
  // ws.onmessage = (m) => { const e = JSON.parse(m.data); if (!seen.has(e.id)) { seen.add(e.id); onEvent(e); } };
  // reconnect with backoff on close.
  // return () => ws.close();
  throw new Error("scaffold — see docs/09 + docs/10");
}
