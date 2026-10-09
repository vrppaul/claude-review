import type { ServerPush, SessionMessage, Welcome } from '$lib/types';

/** Which run of the review the fake server is. */
export const THIS_RUN = 'this-run';

/** What the server says first on a connection: to this run, handed nothing it missed unless told otherwise. */
export function welcome(given: Partial<Welcome> = {}): Welcome {
	return { type: 'welcome', instance: THIS_RUN, sequence: 0, resumed: false, ...given };
}

/** The session socket, as far as a test needs one. */
type Listener = (event: { data?: string }) => void;

/** A socket the test opens, closes and speaks through for the server. */
export class FakeSocket {
	static readonly CONNECTING = 0;
	static readonly OPEN = 1;
	static readonly CLOSED = 3;
	static opened: FakeSocket[] = [];
	readyState = FakeSocket.CONNECTING;
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

	close() {
		this.readyState = FakeSocket.CLOSED;
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
