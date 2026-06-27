// ChatSteering — the Research Manager conversation + steering controls. Shows agent.text; sends
// user.message via POST /sessions/{id}/message; "Stop/redirect" -> POST /interrupt; approve gated tools
// (always_ask) -> POST /confirm. Uses `processed_at` to show pending vs acknowledged (docs/10). STATUS: scaffold.
export function ChatSteering() {
  return <div data-testid="chat-steering">ChatSteering (scaffold)</div>;
}
