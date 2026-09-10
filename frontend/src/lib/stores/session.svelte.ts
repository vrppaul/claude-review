/**
 * The connection that keeps the review alive.
 *
 * The server stays up for as long as a browser holds this socket, and winds
 * down shortly after the last one closes. A poll could not do the same job:
 * a background tab has its timers throttled to about once a minute, so a
 * review left open in another tab looked abandoned and the server exited
 * from under it, taking the comments with it.
 *
 * It is open in both directions from the start, so the server can push —
 * and so the browser can say, once, where the review had got to. A server
 * restarted mid-review comes back believing it is round one; the browser is
 * the only side that still knows better.
 */

export type ServerMessage = { type: string; [key: string]: unknown };

let socket: WebSocket | null = null;
let retryDelay = 500;
// Said again on every reconnection, because a reconnection may be to a
// server that has just come up knowing nothing
let greeting: (() => unknown) | null = null;

/** Connect, and keep reconnecting if the socket drops while the page lives. */
export function openSession(
  onMessage: (message: ServerMessage) => void,
  hello?: () => unknown,
): () => void {
  greeting = hello ?? null;
  let closedByUs = false;

  const connect = () => {
    if (closedByUs) return;
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${location.host}/api/session`);

    socket.addEventListener("open", () => {
      retryDelay = 500;
      tellServer();
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
    greeting = null;
    if (telling !== null) clearTimeout(telling);
    telling = null;
    socket?.close();
    socket = null;
  };
}

// Typing a summary saves the draft on every keystroke, and each save is a
// reason to tell the server what the review now holds. Once a second is
// often enough for something nobody reads until they ask for it.
const AT_MOST_EVERY = 1000;
let toldAt = 0;
let telling: ReturnType<typeof setTimeout> | null = null;

/**
 * Say the greeting again, now that there is more to say.
 *
 * The socket opens while the draft is still being read, so what the browser
 * knows about the review arrives a moment after the connection does — and
 * every thread written afterwards changes it again.
 */
export function tellServer(): void {
  if (!greeting || socket?.readyState !== WebSocket.OPEN) return;

  const due = toldAt + AT_MOST_EVERY - Date.now();
  if (due > 0) {
    // Trailing rather than dropped: the last state is the one that matters
    if (telling === null) {
      telling = setTimeout(() => {
        telling = null;
        tellServer();
      }, due);
    }
    return;
  }

  toldAt = Date.now();
  socket.send(JSON.stringify(greeting()));
}
