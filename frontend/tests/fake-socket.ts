import type { ServerPush, SessionMessage, Welcome } from '$lib/types';

/** Which run of the review the fake server is. */
export const THIS_RUN = 'this-run';
/** What the review a test opens names itself, unless it says otherwise: the name its draft is kept under. */
export const REVIEW_IDENTITY = 'review-under-test';

/** What the server says first on a connection: to this review and run, handed nothing it missed unless told otherwise. */
export function welcome(given: Partial<Welcome> = {}): Welcome {
	return { type: 'welcome', identity: REVIEW_IDENTITY, instance: THIS_RUN, sequence: 0, resumed: false, ...given };
}

/** The session socket, as far as a test needs one. */
type Listener = (event: { data?: string }) => void;

/** A socket the test opens, closes and speaks through for the server. */
export class FakeSocket {
	static readonly CONNECTING = 0;
	static readonly OPEN = 1;
	static readonly CLOSING = 2;
	static readonly CLOSED = 3;
	static opened: FakeSocket[] = [];
	readyState = FakeSocket.CONNECTING;
	/** Whether the page let the socket go, rather than the server dropping it. */
	closedByThePage = false;
	sent: string[] = [];
	private readonly listeners = new Map<string, Listener[]>();

	constructor(readonly url: string) {
		FakeSocket.opened.push(this);
	}

	addEventListener(kind: string, listener: Listener) {
		this.listeners.set(kind, [...(this.listeners.get(kind) ?? []), listener]);
	}

	send(text: string) {
		this.sent.push(text);
	}

	/**
	 * The page let the socket go. As in a browser, it is closing at once and
	 * says it has closed a moment later, once; closing it again does nothing.
	 */
	close() {
		if (this.readyState === FakeSocket.CLOSING || this.readyState === FakeSocket.CLOSED) return;
		this.closedByThePage = true;
		this.readyState = FakeSocket.CLOSING;
		queueMicrotask(() => {
			this.readyState = FakeSocket.CLOSED;
			this.emit('close');
		});
	}

	/** The server took the connection. */
	accept() {
		this.readyState = FakeSocket.OPEN;
		this.emit('open');
	}

	/** The connection went from under the page: the server stopped, or restarted. */
	drop() {
		this.readyState = FakeSocket.CLOSED;
		this.emit('close');
	}

	emit(kind: string, data?: string) {
		for (const listener of this.listeners.get(kind) ?? []) listener(data === undefined ? {} : { data });
	}

	/** The server said something down this socket. */
	say(message: SessionMessage) {
		this.emit('message', JSON.stringify(message));
	}

	/** The server delivered a push, numbered in its telling. */
	deliver(push: ServerPush, sequence: number) {
		this.say({ type: 'delivery', sequence, push });
	}

	/** What the page said down this socket, read back. */
	get said(): unknown[] {
		return this.sent.map((text) => JSON.parse(text));
	}
}

export function latestSocket(): FakeSocket {
	const socket = FakeSocket.opened.at(-1);
	if (!socket) throw new Error('The page has not opened a socket');
	return socket;
}
