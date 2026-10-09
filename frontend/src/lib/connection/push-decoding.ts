/**
 * Reading what the server pushes down the session socket.
 *
 * Only the kind is checked: the rest of a push's shape is the server's own,
 * generated from its schemas, and a server and page of different releases
 * differ in kinds first. A push of a kind this page does not know is
 * reported and passed over.
 */

import type { ServerPush } from "$lib/types";

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
 * A push from the server, or null when it is not one this page can read.
 *
 * Only the reading is forgiven: a fault in whatever handles a push is a
 * fault, and is left to surface.
 */
export function decodePush(data: unknown): ServerPush | null {
  try {
    const parsed: unknown = JSON.parse(String(data));
    if (isServerPush(parsed)) return parsed;
  } catch {
    // Reported below with everything else that cannot be read
  }
  console.warn("claude-review: a push from the server could not be read", data);
  return null;
}

/** Whether a message is a push of a kind this page knows. */
function isServerPush(value: unknown): value is ServerPush {
  if (typeof value !== "object" || value === null || !("type" in value)) {
    return false;
  }
  return (
    typeof value.type === "string" && Object.hasOwn(PUSH_KINDS, value.type)
  );
}
