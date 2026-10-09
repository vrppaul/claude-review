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
 *
 * Every push arrives numbered. When the socket drops — a laptop asleep, a
 * network gone — the connection comes back naming the run of the review it
 * was reading and the last number it was handed, and is handed what it
 * missed. When the review cannot hand over all of it, the page is asked to
 * catch up, and what arrives meanwhile waits until it has.
 */

import { decodeSessionMessage } from '$lib/connection/session-messages';
import type { Delivery, ServerPush, SessionHello, Welcome } from '$lib/types';

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

/** What the page does with what the connection brings it. */
export interface PushReceiver {
	/** Take in one push. */
	take(push: ServerPush): void;
	/**
	 * Learn again what the pushes would have said: the connection came back
	 * to a review that could not hand over everything it missed. Settles once
	 * done, whether or not it could; what went wrong, it says itself.
	 */
	catchUp(): Promise<void>;
}

/** The page's socket: held open, reconnected when it drops, and spoken through. */
export class PageConnection {
	readonly #url: string;
	#socket: WebSocket | null = null;
	// Set once the page lets go; nothing connects again after it
	#closed = false;
	#retryDelay = FIRST_RETRY;
	#retrying: ReturnType<typeof setTimeout> | null = null;
	// Which run of the review this page was welcomed by, and the number of the
	// last push it was handed: what it names when it comes back
	#instance: string | null = null;
	#sequence: number | null = null;
	// What arrives while the page cannot take it: before its review is open —
	// a reply or a raised thread taken in before the draft is restored would
	// be overwritten by it — and while it catches up
	#held: ServerPush[] = [];
	#receiver: PushReceiver | null = null;
	// Whether something was missed that the page has still to catch up on,
	// and whether it is catching up now
	#behind = false;
	#catchingUp = false;
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
		this.#receiver = null;
		this.#held = [];
	}

	/** Hand over what arrived while the page was not ready, and everything from now on. */
	deliverTo(receiver: PushReceiver): void {
		this.#receiver = receiver;
		this.#serve();
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
		const socket = new WebSocket(this.#address());
		socket.addEventListener('open', () => this.#opened());
		socket.addEventListener('message', (event) => this.#received(event.data));
		socket.addEventListener('close', () => this.#lost());
		this.#socket = socket;
	}

	/** Where to connect: naming, once there is one, the run of the review and the last push handed. */
	#address(): string {
		if (this.#instance === null || this.#sequence === null) return this.#url;
		const resume = new URLSearchParams({ instance: this.#instance, after: String(this.#sequence) });
		return `${this.#url}?${resume.toString()}`;
	}

	#opened(): void {
		this.#retryDelay = FIRST_RETRY;
		this.#sayHello();
	}

	#received(data: unknown): void {
		const message = decodeSessionMessage(data);
		if (message === null) return;
		if (message.type === 'welcome') this.#welcomed(message);
		else this.#delivered(message);
	}

	/**
	 * A connection made. One that was handed what it missed reads on from
	 * where it was; any other reads on from where the review's telling has
	 * got to, and one that came back that way has missed something.
	 */
	#welcomed(welcome: Welcome): void {
		const cameBack = this.#instance !== null;
		this.#instance = welcome.instance;
		if (welcome.resumed) return;
		this.#sequence = welcome.sequence;
		if (cameBack) {
			this.#behind = true;
			this.#serve();
		}
	}

	#delivered(delivery: Delivery): void {
		this.#sequence = delivery.sequence;
		this.#held.push(delivery.push);
		this.#serve();
	}

	/**
	 * Hand the page what is held, unless it cannot take it yet: its review is
	 * not open, or it is catching up — which, owed, comes first.
	 */
	#serve(): void {
		const receiver = this.#receiver;
		if (receiver === null || this.#catchingUp) return;
		if (this.#behind) {
			this.#behind = false;
			this.#catchingUp = true;
			void receiver.catchUp().finally(() => this.#caughtUp());
			return;
		}
		const waiting = this.#held;
		this.#held = [];
		for (const push of waiting) receiver.take(push);
	}

	#caughtUp(): void {
		this.#catchingUp = false;
		this.#serve();
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
