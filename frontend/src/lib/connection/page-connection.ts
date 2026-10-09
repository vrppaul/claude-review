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
 * and so the browser can say where the review had got to. A server
 * restarted mid-review comes back believing it is round one; the browser is
 * the only side that still knows better.
 */

import { decodePush } from '$lib/connection/push-decoding';
import type { ServerPush, SessionHello } from '$lib/types';

/** How long the first attempt to reconnect waits, in milliseconds. */
export const FIRST_RETRY = 500;
/** How much longer each attempt waits than the one before. */
export const RETRY_GROWTH = 2;
/** The longest any attempt waits: the server may simply be slow to come back. */
export const LONGEST_RETRY = 5000;
// Threads change in bursts — a retake moves every one, a reader reads and
// folds several in a row — and each change is a reason to tell the server.
// Once a second is often enough for something nobody reads until they ask.
export const HELLO_AT_MOST_EVERY = 1000;

/** Where the session socket is, on the server that served this page. */
export function sessionUrl(page: Location): string {
	const protocol = page.protocol === 'https:' ? 'wss' : 'ws';
	return `${protocol}://${page.host}/api/session`;
}

/** Whatever the page does with a push once it can take one. */
export type PushHandler = (push: ServerPush) => void;

/** The page's socket: held open, reconnected when it drops, and spoken through. */
export class PageConnection {
	readonly #url: string;
	#socket: WebSocket | null = null;
	// Set once the page lets go; nothing connects again after it
	#closed = false;
	#retryDelay = FIRST_RETRY;
	#retrying: ReturnType<typeof setTimeout> | null = null;
	// What arrives before the page can take it. Handed over once it can: a
	// reply or a raised thread taken in before the draft is restored would be
	// overwritten by it, or find no thread to land in.
	#held: ServerPush[] = [];
	#handler: PushHandler | null = null;
	// What the page last said it holds. Said again on every connection,
	// because a connection may be to a server that has just come up knowing
	// nothing.
	#hello: SessionHello | null = null;
	#toldAt = 0;
	#telling: ReturnType<typeof setTimeout> | null = null;

	constructor(url: string) {
		this.#url = url;
	}

	/** Connect, and keep connecting again whenever the socket drops, until closed. */
	open(): void {
		this.#connect();
	}

	/** Let the socket go for good. */
	close(): void {
		this.#closed = true;
		if (this.#retrying !== null) clearTimeout(this.#retrying);
		if (this.#telling !== null) clearTimeout(this.#telling);
		this.#retrying = null;
		this.#telling = null;
		this.#socket?.close();
		this.#socket = null;
		this.#handler = null;
		this.#held = [];
	}

	/** Hand over what arrived while the page was not ready, and everything from now on. */
	deliverTo(handler: PushHandler): void {
		this.#handler = handler;
		const waiting = this.#held;
		this.#held = [];
		for (const push of waiting) handler(push);
	}

	/**
	 * Say what the page now holds: at once if it has not spoken for a while,
	 * and otherwise a moment later, saying only the latest.
	 */
	greet(hello: SessionHello): void {
		this.#hello = hello;
		this.#sayHello();
	}

	#connect(): void {
		if (this.#closed) return;
		const socket = new WebSocket(this.#url);
		socket.addEventListener('open', () => this.#opened());
		socket.addEventListener('message', (event) => this.#received(event.data));
		socket.addEventListener('close', () => this.#lost());
		this.#socket = socket;
	}

	#opened(): void {
		this.#retryDelay = FIRST_RETRY;
		this.#sayHello();
	}

	#received(data: unknown): void {
		const push = decodePush(data);
		if (push === null) return;
		if (this.#handler === null) this.#held.push(push);
		else this.#handler(push);
	}

	/** The server may simply be slow to come back; back off rather than spin. */
	#lost(): void {
		if (this.#closed) return;
		this.#retrying = setTimeout(() => this.#retry(), this.#retryDelay);
		this.#retryDelay = Math.min(this.#retryDelay * RETRY_GROWTH, LONGEST_RETRY);
	}

	#retry(): void {
		this.#retrying = null;
		this.#connect();
	}

	#sayHello(): void {
		if (this.#hello === null || this.#socket?.readyState !== WebSocket.OPEN) {
			return;
		}
		const due = this.#toldAt + HELLO_AT_MOST_EVERY - Date.now();
		if (due > 0) {
			// Trailing rather than dropped: the last state is the one that matters
			this.#telling ??= setTimeout(() => this.#sayHelloLater(), due);
			return;
		}
		this.#toldAt = Date.now();
		this.#socket.send(JSON.stringify(this.#hello));
	}

	#sayHelloLater(): void {
		this.#telling = null;
		this.#sayHello();
	}
}
