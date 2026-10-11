import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FakeSocket, latestSocket, welcome } from './fake-socket';
import { FIRST_RETRY, HELLO_AT_MOST_EVERY, LONGEST_RETRY, RETRY_GROWTH } from '$lib/connection/page-connection';
import { A_CHAT, A_REPLY, connected, opened, PageThatBreaksOn, RecordingPage, TOLD_BEFORE } from './recording-page';

// The second attempt to reconnect waits longer than the first
const SECOND_RETRY = RETRY_GROWTH * FIRST_RETRY;
// How far the review's telling has got when the page catches up
const TOLD_SINCE = 9;

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

	it('passes over what it cannot read and keeps listening', () => {
		const page = new RecordingPage();
		const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
		const connection = connected(page);
		const socket = latestSocket();
		socket.accept();
		socket.say(welcome({ sequence: TOLD_BEFORE, resumed: true }));

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

	it('says so when the page fails to take a push in, and goes on handing it the next', () => {
		const fault = vi.spyOn(console, 'error').mockImplementation(() => undefined);
		const page = new PageThatBreaksOn('reply');
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE, resumed: true }));

		latestSocket().deliver(A_REPLY, TOLD_BEFORE + 1);
		latestSocket().deliver(A_CHAT, TOLD_BEFORE + 2);

		expect(fault).toHaveBeenCalledOnce();
		expect(page.heard).toEqual([A_CHAT]);
		connection.close();
	});

	it('hands over what waited behind a push the page failed to take in', async () => {
		vi.spyOn(console, 'error').mockImplementation(() => undefined);
		const page = new PageThatBreaksOn('reply');
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_SINCE }));
		latestSocket().deliver(A_REPLY, TOLD_SINCE + 1);
		latestSocket().deliver(A_CHAT, TOLD_SINCE + 2);

		page.finishCatchingUp();

		await vi.waitFor(() => expect(page.heard).toEqual([A_CHAT]));
		connection.close();
	});

	it('connects again after the server goes, waiting longer after each failure', () => {
		const connection = opened();
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
		const connection = opened();
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
		const connection = opened();
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
		const connection = opened();
		const socket = latestSocket();

		connection.close();
		socket.drop();
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(1);
	});

	it('does not connect again when closed while waiting to', () => {
		const connection = opened();
		latestSocket().drop();

		connection.close();
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(1);
	});

	it('says hello on every connection once its own review has welcomed it, to a server that may have just come up', () => {
		const connection = connected();
		connection.greet(inRound(3));

		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		expect(latestSocket().said).toEqual([inRound(3)]);

		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(latestSocket().said).toEqual([inRound(3)]);
		connection.close();
	});

	it('tells the server what changed at most once a second, ending on the latest', () => {
		const connection = connected();
		const socket = latestSocket();
		socket.accept();
		socket.say(welcome({ resumed: true }));
		connection.greet(inRound(1));

		connection.greet(inRound(2));
		connection.greet(inRound(3));
		expect(socket.said).toEqual([inRound(1)]);

		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);

		expect(socket.said).toEqual([inRound(1), inRound(3)]);
		connection.close();
	});

	it('says nothing before its own review has welcomed it, and what it holds once it has', () => {
		const connection = connected();

		connection.greet(inRound(1));
		latestSocket().accept();
		connection.greet(inRound(2));
		vi.advanceTimersByTime(HELLO_AT_MOST_EVERY);
		expect(latestSocket().said).toEqual([]);

		latestSocket().say(welcome({ resumed: true }));

		expect(latestSocket().said).toEqual([inRound(2)]);
		connection.close();
	});

	it('tells the page each time its socket drops, and each time its own review welcomes it again', () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));

		latestSocket().drop();
		const whileDown = { reached: page.reachedTimes, lost: page.lostTimes };
		vi.advanceTimersByTime(FIRST_RETRY);
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));

		expect(whileDown).toEqual({ reached: 1, lost: 1 });
		expect({ reached: page.reachedTimes, lost: page.lostTimes }).toEqual({ reached: 2, lost: 1 });
		connection.close();
	});

	it('says nothing to another review answering on its port, and lets go of it for good', () => {
		const page = new RecordingPage();
		const connection = connected(page);
		connection.greet(inRound(2));
		const socket = latestSocket();
		socket.accept();

		socket.say(welcome({ identity: 'the-next-review-on-this-port' }));
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(socket.said).toEqual([]);
		expect(socket.readyState).toBe(FakeSocket.CLOSED);
		expect(FakeSocket.opened.at(-1)).toBe(socket);
		expect(page.strayedOff).toBe(true);
		expect(page.catchUps).toBe(0);
	});
});
