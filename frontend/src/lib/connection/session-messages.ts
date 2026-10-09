/**
 * Reading what the server says down the session socket: a welcome on every
 * connection, then each push in a numbered delivery.
 *
 * Only the kinds are checked: the rest of a message's shape is the server's
 * own, generated from its schemas, and a server and page of different
 * releases differ in kinds first. A message of a kind this page does not
 * know is reported and passed over.
 */

import type { ServerPush, SessionMessage } from '$lib/types';

/**
 * Every kind of push this page knows. Keyed by the generated union's own
 * kinds, so the compiler refuses a kind left out or one the server never
 * sends.
 */
const PUSH_KINDS: Record<ServerPush['type'], true> = {
	reply: true,
	answerer: true,
	chat: true,
	progress: true,
	show: true,
	status: true,
	point: true,
	changed: true,
	round: true,
	diff: true
};

/** How each kind of message is checked, once its kind is known: a delivery by the push it carries. */
const MESSAGE_CHECKS: Record<SessionMessage['type'], (message: object) => boolean> = {
	welcome: () => true,
	delivery: (message) => 'push' in message && isServerPush(message.push)
};

/**
 * A message from the server, or null when it is not one this page can read.
 *
 * Only the reading is forgiven: a fault in whatever handles a message is a
 * fault, and is left to surface.
 */
export function decodeSessionMessage(data: unknown): SessionMessage | null {
	try {
		const parsed: unknown = JSON.parse(String(data));
		if (isSessionMessage(parsed)) return parsed;
	} catch {
		// Reported below with everything else that cannot be read
	}
	console.warn('claude-review: a message from the server could not be read', data);
	return null;
}

function isSessionMessage(value: unknown): value is SessionMessage {
	return hasKind(value) && isMessageKind(value.type) && MESSAGE_CHECKS[value.type](value);
}

function isMessageKind(kind: string): kind is SessionMessage['type'] {
	return Object.hasOwn(MESSAGE_CHECKS, kind);
}

function isServerPush(value: unknown): value is ServerPush {
	return hasKind(value) && Object.hasOwn(PUSH_KINDS, value.type);
}

function hasKind(value: unknown): value is { type: string } {
	return typeof value === 'object' && value !== null && 'type' in value && typeof value.type === 'string';
}
