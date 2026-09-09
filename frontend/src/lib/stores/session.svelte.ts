/**
 * The connection that keeps the review alive.
 *
 * The server stays up for as long as a browser holds this socket, and winds
 * down shortly after the last one closes. A poll could not do the same job:
 * a background tab has its timers throttled to about once a minute, so a
 * review left open in another tab looked abandoned and the server exited
 * from under it, taking the comments with it.
 *
 * It is open in both directions from the start, so the server can push.
 */

export type ServerMessage = { type: string; [key: string]: unknown };

let socket: WebSocket | null = null;
let retryDelay = 500;

/** Connect, and keep reconnecting if the socket drops while the page lives. */
export function openSession(
  onMessage: (message: ServerMessage) => void,
): () => void {
  let closedByUs = false;

  const connect = () => {
    if (closedByUs) return;
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${location.host}/api/session`);

    socket.addEventListener("open", () => {
      retryDelay = 500;
    });
    socket.addEventListener("message", (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch {
        // A message we cannot read is not worth breaking the review over
      }
    });
    socket.addEventListener("close", () => {
      if (closedByUs) return;
      // The server may simply be slow to come back; back off rather than spin
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 5000);
    });
  };

  connect();

  return () => {
    closedByUs = true;
    socket?.close();
    socket = null;
  };
}
