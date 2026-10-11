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
 * Every push arrives numbered. Once the page can take pushes, each
 * connection names where its telling stands — the run of the review it was
 * reading and how far it had heard it, which the page keeps — and is handed
 * what came after.
 * When the review cannot hand over all of it, the page is asked to catch up,
 * and what arrives meanwhile waits until it has.
 *
 * The port outlives the review: once it is over, the next review of the
 * same thing — or of anything, on a port named twice — may answer there.
 * The page says nothing until the review that welcomes it names itself as
 * its own; one that names itself otherwise is let go for good, unheard and
 * untold, so it is neither handed this page's threads nor held open by it.
 */

import { decodeSessionMessage } from '$lib/connection/session-messages';
import type { Delivery, ServerPush, SessionHello, TellingPosition, Welcome } from '$lib/types';

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
	/** Which review the page shows, by the name the review gives itself. */
	identity: string;
	/** Where the page's telling stands: the run of the review, and how far the page has heard it. */
	told: () => TellingPosition;
	/** Take in one push, and where it stands in the telling. */
	take: (push: ServerPush, at: TellingPosition) => void;
	/**
	 * Learn again what the pushes would have said: the review could not hand
	 * over everything missed before `from`, where the telling now goes on.
	 * Settles once done, whether or not it could; what went wrong, it says
	 * itself.
	 */
	catchUp: (from: TellingPosition) => Promise<void>;
	/** Another review answered on the port: the page's own is over, and the connection has let go of it. */
	strayed: () => void;
}

/** A push waiting to be handed over, with where it stands in the telling. */
interface HeldPush {
	push: ServerPush;
	at: TellingPosition;
}

/** The page's socket: held open, reconnected when it drops, and spoken through. */
export class PageConnection {
	readonly #url: string;
	#socket: WebSocket | null = null;
	// Set once the page lets go; nothing connects again after it
	#closed = false;
	#retryDelay = FIRST_RETRY;
	#retrying: ReturnType<typeof setTimeout> | null = null;
	// What takes what the socket brings. Until there is one, the socket only
	// holds the review on screen: it named no place in the telling to go on
	// from, and is replaced by one that does once the page can say it.
	#receiver: PushReceiver | null = null;
	// The socket that held the review on screen, kept until the one replacing
	// it is open: a review with no socket at all is a review the server ends
	#holding: WebSocket | null = null;
	// Which run of the review the socket open now is talking to, as its
	// welcome said: what a delivery's number counts in. None until the page's
	// own review has welcomed it, and nothing is said before then.
	#instance: string | null = null;
	// What arrives while the page catches up, handed over once it has
	#held: HeldPush[] = [];
	// Where the telling went on after something was missed, while the page
	// has still to catch up on it; and whether it is catching up now
	#resumedAt: TellingPosition | null = null;
	#catchingUp = false;
	// What the page last said it holds. Said again on every connection,
	// because a connection may be to a server that has just come up knowing
	// nothing. Then when it was last said, and what says the latest once it
	// may be said again.
	#hello: SessionHello | null = null;
	#helloSaidAt = 0;
	#helloTimer: ReturnType<typeof setTimeout> | null = null;

	constructor(url: string) {
		this.#url = url;
	}

	/**
	 * Connect, and keep connecting again whenever the socket drops, until
	 * closed. Holding the socket is what tells the server the review is on
	 * screen, so it is held before anything else, however long the review
	 * takes to read.
	 */
	open(): void {
		this.#connect();
	}

	/** Let the socket go for good. */
	close(): void {
		this.#closed = true;
		this.#stopRetrying();
		if (this.#helloTimer !== null) clearTimeout(this.#helloTimer);
		this.#helloTimer = null;
		this.#letGoOfHolding();
		this.#socket?.close();
		this.#socket = null;
		this.#receiver = null;
		this.#held = [];
		this.#resumedAt = null;
	}

	/**
	 * Hand everything from now on to the page, going on from where its
	 * telling stands. The socket held until now named no such place, so one
	 * that does takes its place once it is open, and the review hands over
	 * whatever it told in between.
	 */
	deliverTo(receiver: PushReceiver): void {
		this.#receiver = receiver;
		// Not open yet: opening will name the place
		if (this.#socket === null) return;
		this.#stopRetrying();
		this.#holding = this.#socket;
		this.#connect();
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
		this.#instance = null;
		const socket = new WebSocket(this.#address());
		socket.addEventListener('open', () => this.#opened(socket));
		socket.addEventListener('message', (event) => this.#received(socket, event.data));
		socket.addEventListener('close', () => this.#lost(socket));
		this.#socket = socket;
	}

	/** Where to connect: naming, once the page can say it, the run of the review and how far the page has heard it. */
	#address(): string {
		const told = this.#receiver?.told();
		if (told === undefined) return this.#url;
		const resume = new URLSearchParams({ instance: told.instance, after: String(told.sequence) });
		return `${this.#url}?${resume.toString()}`;
	}

	#opened(socket: WebSocket): void {
		if (socket !== this.#socket) return;
		this.#letGoOfHolding();
		this.#retryDelay = FIRST_RETRY;
	}

	#letGoOfHolding(): void {
		this.#holding?.close();
		this.#holding = null;
	}

	/** What a socket said; one replaced since is no longer listened to. */
	#received(socket: WebSocket, data: unknown): void {
		const receiver = this.#receiver;
		if (socket !== this.#socket || receiver === null) return;
		const message = decodeSessionMessage(data);
		if (message === null) return;
		if (message.type === 'welcome') this.#welcomed(message, receiver);
		else this.#delivered(message, receiver);
	}

	/**
	 * A connection made — to the page's own review, or to another that runs
	 * on the port now, which is let go of. One handed what it missed reads on
	 * from where it was; any other has missed something it cannot be handed,
	 * and reads on from where the review's telling has got, once the page has
	 * caught up. Either way the page says what it holds.
	 */
	#welcomed(welcome: Welcome, receiver: PushReceiver): void {
		if (welcome.identity !== receiver.identity) {
			this.close();
			receiver.strayed();
			return;
		}
		this.#instance = welcome.instance;
		this.#sayHello();
		if (welcome.resumed) return;
		this.#resumedAt = { instance: welcome.instance, sequence: welcome.sequence };
		this.#serve(receiver);
	}

	#delivered(delivery: Delivery, receiver: PushReceiver): void {
		// The server welcomes every connection first; a number counted in no
		// run that was named cannot be placed
		if (this.#instance === null) return;
		this.#held.push({ push: delivery.push, at: { instance: this.#instance, sequence: delivery.sequence } });
		this.#serve(receiver);
	}

	/**
	 * Hand the page what is held, in order, unless it is catching up —
	 * which, owed, comes first.
	 */
	#serve(receiver: PushReceiver): void {
		if (this.#catchingUp) return;
		const resumedAt = this.#resumedAt;
		if (resumedAt !== null) {
			this.#resumedAt = null;
			this.#catchingUp = true;
			void receiver.catchUp(resumedAt).finally(() => this.#caughtUp(receiver));
			return;
		}
		for (let held = this.#held.shift(); held !== undefined; held = this.#held.shift()) {
			handOver(receiver, held);
		}
	}

	#caughtUp(receiver: PushReceiver): void {
		this.#catchingUp = false;
		if (receiver === this.#receiver) this.#serve(receiver);
	}

	/** The server may simply be slow to come back; back off rather than spin. */
	#lost(socket: WebSocket): void {
		if (this.#closed || socket !== this.#socket) return;
		this.#retrying = setTimeout(() => this.#retry(), this.#retryDelay);
		this.#retryDelay = Math.min(this.#retryDelay * RETRY_GROWTH, LONGEST_RETRY);
	}

	#retry(): void {
		this.#retrying = null;
		this.#connect();
	}

	#stopRetrying(): void {
		if (this.#retrying !== null) clearTimeout(this.#retrying);
		this.#retrying = null;
	}

	#sayHello(): void {
		if (this.#hello === null || this.#instance === null || this.#socket?.readyState !== WebSocket.OPEN) {
			return;
		}
		const due = this.#helloSaidAt + HELLO_AT_MOST_EVERY - Date.now();
		if (due > 0) {
			// Trailing rather than dropped: the last state is the one that matters
			this.#helloTimer ??= setTimeout(() => this.#sayHelloLater(), due);
			return;
		}
		this.#helloSaidAt = Date.now();
		this.#socket.send(JSON.stringify(this.#hello));
	}

	#sayHelloLater(): void {
		this.#helloTimer = null;
		this.#sayHello();
	}
}

/**
 * Hand one push to the page. One it fails to take in is a fault of the
 * page's own, said where faults are said; the pushes behind it are not at
 * fault, and still go through.
 */
function handOver(receiver: PushReceiver, held: HeldPush): void {
	try {
		receiver.take(held.push, held.at);
	} catch (error) {
		console.error('claude-review: a push from the server could not be taken in', held.push, error);
	}
}
