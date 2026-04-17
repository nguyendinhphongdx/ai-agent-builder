export interface SocketEnvelope {
  event: string;
  payload: Record<string, unknown>;
  timestamp: string;
}
