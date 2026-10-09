import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FakeSocket, latestSocket, THIS_RUN, welcome } from './fake-socket';
import type { ServerPush } from '$lib/types';
import {
	FIRST_RETRY,
	HELLO_AT_MOST_EVERY,
	LONGEST_RETRY,
	PageConnection,
	RETRY_GROWTH,
	type PushReceiver
} from '$lib/connection/page-connection';

// Pushes as the server sends them
const A_REPLY: ServerPush = { type: 'reply', thread_id: 'comment-1', question_id: null, body: 'first' };
const A_CHAT: ServerPush = { type: 'chat', message_id: null, body: 'second', files: [] };
const A_SHOW: ServerPush = { type: 'show', file: 'a.py' };

// The second attempt to reconnect waits longer than the first
const SECOND_RETRY = RETRY_GROWTH * FIRST_RETRY;

// Where the page's socket is; the fake socket only keeps it
const SESSION_URL = 'ws://review.test/api/session';

// How far the review's telling had got when the page connected
const TOLD_BEFORE = 3;
// How far it has got when a page that dropped comes back
const TOLD_SINCE = 9;

/** A page's connection, opened. */
function connected(): PageConnection {
	const connection = new PageConnection(SESSION_URL);
	connection.open();
	return connection;
}

/** A page that notes what it is handed, and catches up when asked, finishing when the test says. */
class RecordingPage implements PushReceiver {
	readonly heard: ServerPush[] = [];
	catchUps = 0;
	#finish: (() => void) | null = null;

	take(push: ServerPush): void {
		this.heard.push(push);
	}

	catchUp(): Promise<void> {
		this.catchUps += 1;
		return new Promise((resolve) => (this.#finish = resolve));
	}

	/** The page has caught up; what the connection held is handed over once it hears so. */
	finishCatchingUp(): void {
		this.#finish?.();
	}
}

/** Drop the socket and let the connection come back on a socket of its own. */
function dropAndComeBack(): void {
	latestSocket().drop();
	vi.advanceTimersByTime(FIRST_RETRY);
	latestSocket().accept();
}

/** What a page says when it holds no threads, in this round. */
function inRound(round: number) {
	return { round, threads: null };
}

describe('the session socket', () => {
	beforeEach(() => {
		FakeSocket.opened = [];
		vi.stubGlobal('WebSocket', FakeSocket);
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('holds what arrives before the page can take it, then hands it over in order', () => {
		const page = new RecordingPage();
		const connection = connected();
		const socket = latestSocket();
		socket.accept();
		socket.say(welcome());

		socket.deliver(A_REPLY, 1);
		socket.deliver(A_CHAT, 2);
		expect(page.heard).toEqual([]);

		connection.deliverTo(page);
		socket.deliver(A_SHOW, 3);

		expect(page.heard).toEqual([A_REPLY, A_CHAT, A_SHOW]);
		connection.close();
	});

	it('passes over what it cannot read and keeps listening', () => {
		const page = new RecordingPage();
		const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
		const connection = connected();
		connection.deliverTo(page);
		const socket = latestSocket();

		socket.emit('message', 'not json');
		socket.emit('message', JSON.stringify({ text: 'no type' }));
		socket.emit('message', JSON.stringify({ type: 'teleport', to: 'elsewhere' }));
		socket.emit('message', JSON.stringify({ type: 'delivery', sequence: 1, push: { type: 'teleport' } }));
		socket.emit('message', JSON.stringify(A_REPLY));
		socket.deliver(A_REPLY, 1);

		expect(page.heard).toEqual([A_REPLY]);
		expect(warn).toHaveBeenCalledTimes(5);
		connection.close();
	});

	it('does not hide a fault in whatever handles a push', () => {
		const connection = connected();
		const page = new RecordingPage();
		page.take = () => {
			throw new Error('handler broke');
		};
		connection.deliverTo(page);

		expect(() => latestSocket().deliver(A_REPLY, 1)).toThrow('handler broke');
		connection.close();
	});

	it('connects the first time naming nothing', () => {
		const connection = connected();

		expect(latestSocket().url).toBe(SESSION_URL);
		connection.close();
	});

	it('comes back naming the run of the review it read and the last push it was handed', () => {
		const connection = connected();
		connection.deliverTo(new RecordingPage());
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE }));
		latestSocket().deliver(A_REPLY, TOLD_BEFORE + 1);

		dropAndComeBack();

		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${TOLD_BEFORE + 1}`);
		connection.close();
	});

	it('reads on from what it was handed when the review hands over what it missed', () => {
		const page = new RecordingPage();
		const connection = connected();
		connection.deliverTo(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE }));

		dropAndComeBack();
		latestSocket().say(welcome({ sequence: TOLD_SINCE, resumed: true }));
		latestSocket().deliver(A_REPLY, TOLD_BEFORE + 1);

		expect(page.catchUps).toBe(0);
		expect(page.heard).toEqual([A_REPLY]);
		connection.close();
	});

	it('never catches up on its first connection: the page reads the review as it opens', () => {
		const page = new RecordingPage();
		const connection = connected();
		connection.deliverTo(page);
		latestSocket().accept();

		latestSocket().say(welcome({ sequence: TOLD_BEFORE }));

		expect(page.catchUps).toBe(0);
		connection.close();
	});

	it('catches up when it comes back without what it missed, holding what arrives meanwhile', async () => {
		const page = new RecordingPage();
		const connection = connected();
		connection.deliverTo(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE }));

		dropAndComeBack();
		latestSocket().say(welcome({ sequence: TOLD_SINCE }));
		latestSocket().deliver(A_REPLY, TOLD_SINCE + 1);

		expect(page.catchUps).toBe(1);
		expect(page.heard).toEqual([]);

		page.finishCatchingUp();

		await vi.waitFor(() => expect(page.heard).toEqual([A_REPLY]));
		dropAndComeBack();
		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${TOLD_SINCE + 1}`);
		connection.close();
	});

	it('catches up once its review is open when it came back without what it missed before then', async () => {
		const page = new RecordingPage();
		const connection = connected();
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE }));
		dropAndComeBack();
		latestSocket().say(welcome({ sequence: TOLD_SINCE }));
		latestSocket().deliver(A_CHAT, TOLD_SINCE + 1);

		connection.deliverTo(page);

		expect(page.catchUps).toBe(1);
		page.finishCatchingUp();
		await vi.waitFor(() => expect(page.heard).toEqual([A_CHAT]));
		connection.close();
	});

	it('connects again after the server goes, waiting longer after each failure', () => {
		const connection = connected();
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
		connection.close();
	});

	it('waits no longer than five seconds between attempts', () => {
		const connection = connected();
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
		connection.close();
	});

	it('starts waiting from the shortest again once a connection holds', () => {
		const connection = connected();
		latestSocket().accept();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		latestSocket().drop();
		vi.advanceTimersByTime(SECOND_RETRY);

		latestSocket().accept();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);

		expect(FakeSocket.opened).toHaveLength(4);
		connection.close();
	});

	it('stays closed once the page has closed it', () => {
		const connection = connected();
		const socket = latestSocket();

		connection.close();
		socket.drop();
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(1);
	});

	it('does not connect again when closed while waiting to', () => {
		const connection = connected();
		latestSocket().drop();

		connection.close();
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(1);
	});

	it('says hello on every connection, to a server that may have just come up', () => {
		const connection = connected();
		connection.greet(inRound(3));

		latestSocket().accept();
		expect(latestSocket().said).toEqual([inRound(3)]);

		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		latestSocket().accept();
		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(latestSocket().said).toEqual([inRound(3)]);
		connection.close();
	});

	it('tells the server what changed at most once a second, ending on the latest', () => {
		const connection = connected();
		const socket = latestSocket();
		socket.accept();
		connection.greet(inRound(1));

		connection.greet(inRound(2));
		connection.greet(inRound(3));
		expect(socket.said).toEqual([inRound(1)]);

		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(socket.said).toEqual([inRound(1), inRound(3)]);
		connection.close();
	});

	it('says nothing before the connection is open, and what it holds once it is', () => {
		const connection = connected();

		connection.greet(inRound(2));
		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);
		expect(latestSocket().said).toEqual([]);

		latestSocket().accept();

		expect(latestSocket().said).toEqual([inRound(2)]);
		connection.close();
	});
});
