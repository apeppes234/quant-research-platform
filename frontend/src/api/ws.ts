export type NormalizedEvent = {
  kind: string;
  id: string;
  type?: string;
  processedAt?: string | null;
  payload: Record<string, unknown>;
};

export type ConnectionStatus = "connecting" | "open" | "closed";

export function connect(
  sessionId: string,
  onEvent: (e: NormalizedEvent) => void,
  onStatus?: (status: ConnectionStatus) => void
): () => void {
  const seen = new Set<string>();
  let closedByClient = false;
  let socket: WebSocket | null = null;
  let retryTimer: number | null = null;
  let attempts = 0;

  const open = () => {
    onStatus?.("connecting");
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${wsProtocol}://${window.location.host}/ws/sessions/${sessionId}/stream`);

    socket.onopen = () => {
      attempts = 0;
      onStatus?.("open");
    };

    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as NormalizedEvent;
      if (!seen.has(event.id)) {
        seen.add(event.id);
        onEvent(event);
      }
    };

    socket.onclose = () => {
      onStatus?.("closed");
      if (!closedByClient) {
        const delay = Math.min(1000 * 2 ** attempts, 10000);
        attempts += 1;
        retryTimer = window.setTimeout(open, delay);
      }
    };
  };

  open();

  return () => {
    closedByClient = true;
    if (retryTimer !== null) {
      window.clearTimeout(retryTimer);
    }
    socket?.close();
  };
}
