import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import type { ServerPush } from '$lib/types';
import {
	dispatchHeld,
	FIRST_RETRY,
	HELLO_AT_MOST_EVERY,
	LONGEST_RETRY,
	openSession,
	RETRY_GROWTH,
	tellServer
} from '$lib/stores/session.svelte';

// Pushes as the server sends them
const A_REPLY: ServerPush = { type: 'reply', thread_id: 'comment-1', question_id: null, text: 'first' };
const A_CHAT: ServerPush = { type: 'chat', message_id: null, text: 'second', files: [] };
const A_SHOW: ServerPush = { type: 'show', file: 'a.py' };

// The second attempt to reconnect waits longer than the first
const SECOND_RETRY = RETRY_GROWTH * FIRST_RETRY;

type Listener = (event: { data?: string }) => void;

/** A socket the test opens, closes and speaks through for the server. */
class FakeSocket {
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
		for (const listener of this.listeners.get(kind) ?? []) listener({ data });
	}

	/** What the page said down this socket, read back. */
	get said(): unknown[] {
		return this.sent.map((text) => JSON.parse(text));
	}
}

function latestSocket(): FakeSocket {
	const socket = FakeSocket.opened.at(-1);
	if (!socket) throw new Error('The page has not opened a socket');
	return socket;
}

function ignore() {}

// The session remembers when it last said hello for as long as the page
// lives, and this file is one page: each test starts on a clock later than
// the last one stopped, so that memory never holds a test's hello back
let clockStart = Date.now();

describe('the session socket', () => {
	beforeEach(() => {
		FakeSocket.opened = [];
		vi.stubGlobal('WebSocket', FakeSocket);
		vi.useFakeTimers({ now: clockStart });
	});

	afterEach(() => {
		clockStart = Date.now() + HELLO_AT_MOST_EVERY;
		vi.useRealTimers();
	});

	it('holds what arrives before the draft is restored, then hands it over in order', () => {
		const heard: ServerPush[] = [];
		const close = openSession((push) => heard.push(push));
		const socket = latestSocket();

		socket.emit('message', JSON.stringify(A_REPLY));
		socket.emit('message', JSON.stringify(A_CHAT));
		expect(heard).toEqual([]);

		dispatchHeld();
		socket.emit('message', JSON.stringify(A_SHOW));

		expect(heard).toEqual([A_REPLY, A_CHAT, A_SHOW]);
		close();
	});

	it('passes over what it cannot read and keeps listening', () => {
		const heard: ServerPush[] = [];
		const warn = vi.spyOn(console, 'warn').mockImplementation(ignore);
		const close = openSession((push) => heard.push(push));
		dispatchHeld();
		const socket = latestSocket();

		socket.emit('message', 'not json');
		socket.emit('message', JSON.stringify({ text: 'no type' }));
		socket.emit('message', JSON.stringify({ type: 'teleport', to: 'elsewhere' }));
		socket.emit('message', JSON.stringify(A_REPLY));

		expect(heard).toEqual([A_REPLY]);
		expect(warn).toHaveBeenCalledTimes(3);
		close();
	});

	it('does not hide a fault in whatever handles a message', () => {
		const close = openSession(() => {
			throw new Error('handler broke');
		});
		dispatchHeld();
		const socket = latestSocket();

		expect(() => socket.emit('message', JSON.stringify(A_REPLY))).toThrow(
			'handler broke'
		);
		close();
	});

	it('connects again after the server goes, waiting longer after each failure', () => {
		const close = openSession(ignore);
		latestSocket().accept();
		latestSocket().drop();

		vi.advanceTimersByTime(FIRST_RETRY - 1);
		expect(FakeSocket.opened).toHaveLength(1);
		vi.advanceTimersByTime(1);
		expect(FakeSocket.opened).toHaveLength(2);

		latestSocket().drop();
		vi.advanceTimersByTime(SECOND_RETRY - 1);
		expect(FakeSocket.opened).toHaveLength(2);
		vi.advanceTimersByTime(1);
		expect(FakeSocket.opened).toHaveLength(3);
		close();
	});

	it('waits no longer than five seconds between attempts', () => {
		const close = openSession(ignore);
		latestSocket().accept();

		// 0.5, 1, 2 and 4 seconds, and then the longest wait rather than 8
		for (let wait = FIRST_RETRY; wait < LONGEST_RETRY; wait *= RETRY_GROWTH) {
			latestSocket().drop();
			vi.advanceTimersByTime(wait);
		}
		const attempts = FakeSocket.opened.length;
		latestSocket().drop();
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(attempts + 1);
		close();
	});

	it('starts waiting from the shortest again once a connection holds', () => {
		const close = openSession(ignore);
		latestSocket().accept();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		latestSocket().drop();
		vi.advanceTimersByTime(SECOND_RETRY);

		latestSocket().accept();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);

		expect(FakeSocket.opened).toHaveLength(4);
		close();
	});

	it('stays closed once the page has closed it', () => {
		const close = openSession(ignore);
		const socket = latestSocket();

		close();
		socket.drop();
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(1);
	});

	it('says hello on every connection, to a server that may have just come up', () => {
		const review = { round: 3 };
		const close = openSession(ignore, () => ({ round: review.round, threads: null }));

		latestSocket().accept();
		expect(latestSocket().said).toEqual([{ round: 3, threads: null }]);

		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		latestSocket().accept();
		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(latestSocket().said).toEqual([{ round: 3, threads: null }]);
		close();
	});

	it('tells the server what changed at most once a second, ending on the latest', () => {
		const review = { round: 1 };
		const close = openSession(ignore, () => ({ round: review.round, threads: null }));
		const socket = latestSocket();
		socket.accept();

		review.round = 2;
		tellServer();
		review.round = 3;
		tellServer();
		expect(socket.said).toEqual([{ round: 1, threads: null }]);

		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(socket.said).toEqual([
			{ round: 1, threads: null },
			{ round: 3, threads: null }
		]);
		close();
	});

	it('says nothing before the connection is open', () => {
		const close = openSession(ignore, () => ({ round: 1, threads: null }));

		tellServer();
		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(latestSocket().said).toEqual([]);
		close();
	});
});
