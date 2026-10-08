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

import type { ServerPush, SessionHello } from "$lib/types";

let socket: WebSocket | null = null;
/** How long the first attempt to reconnect waits, in milliseconds. */
export const FIRST_RETRY = 500;
/** How much longer each attempt waits than the one before. */
export const RETRY_GROWTH = 2;
/** The longest any attempt waits: the server may simply be slow to come back. */
export const LONGEST_RETRY = 5000;

let retryDelay = FIRST_RETRY;
// Said again on every reconnection, because a reconnection may be to a
// server that has just come up knowing nothing
let greeting: (() => SessionHello) | null = null;
// What arrives before the review has restored its draft. Handed over once it
// has: a reply or a raised thread taken in first would be overwritten by the
// draft, or find no thread to land in.
let held: ServerPush[] | null = [];
let deliver: ((push: ServerPush) => void) | null = null;

/** Connect, and keep reconnecting if the socket drops while the page lives. */
export function openSession(
  onPush: (push: ServerPush) => void,
  hello?: () => SessionHello,
): () => void {
  greeting = hello ?? null;
  deliver = onPush;
  held = [];
  let closedByUs = false;

  const connect = () => {
    if (closedByUs) return;
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${protocol}://${location.host}/api/session`);

    socket.addEventListener("open", () => {
      retryDelay = FIRST_RETRY;
      tellServer();
    });
    socket.addEventListener("message", (event) => {
      const push = decode(event.data);
      if (push === null) return;
      if (held !== null) held.push(push);
      else onPush(push);
    });
    socket.addEventListener("close", () => {
      if (closedByUs) return;
      // The server may simply be slow to come back; back off rather than spin
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * RETRY_GROWTH, LONGEST_RETRY);
    });
  };

  connect();

  return () => {
    closedByUs = true;
    greeting = null;
    deliver = null;
    held = [];
    if (telling !== null) clearTimeout(telling);
    telling = null;
    socket?.close();
    socket = null;
  };
}

/** Hand over what arrived while the draft was being restored, and everything from now on. */
export function dispatchHeld(): void {
  const waiting = held ?? [];
  held = null;
  for (const push of waiting) deliver?.(push);
}

/**
 * A push from the server, or null when it is not one this page can read.
 *
 * A push of a kind this page does not know is reported and passed over.
 * Only the reading is forgiven: a fault in whatever handles a push is a
 * fault, and is left to surface.
 */
function decode(data: unknown): ServerPush | null {
  try {
    const parsed: unknown = JSON.parse(String(data));
    if (isServerPush(parsed)) return parsed;
  } catch {
    // Reported below with everything else that cannot be read
  }
  console.warn("claude-review: a push from the server could not be read", data);
  return null;
}

/**
 * Every kind of push this page knows. Keyed by the generated union's own
 * kinds, so the compiler refuses a kind left out or one the server never
 * sends.
 */
const PUSH_KINDS: Record<ServerPush["type"], true> = {
  reply: true,
  answerer: true,
  chat: true,
  progress: true,
  show: true,
  status: true,
  point: true,
  changed: true,
  round: true,
  diff: true,
};

/**
 * Whether a message is a push of a kind this page knows. Only the kind is
 * checked: the rest of its shape is the server's own, generated from its
 * schemas, and a server and page of different releases differ in kinds
 * first.
 */
function isServerPush(value: unknown): value is ServerPush {
  if (typeof value !== "object" || value === null) return false;
  const kind = (value as { type?: unknown }).type;
  return typeof kind === "string" && Object.hasOwn(PUSH_KINDS, kind);
}

// Typing a summary saves the draft on every keystroke, and each save is a
// reason to tell the server what the review now holds. Once a second is
// often enough for something nobody reads until they ask for it.
export const HELLO_AT_MOST_EVERY = 1000;
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

  const due = toldAt + HELLO_AT_MOST_EVERY - Date.now();
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
