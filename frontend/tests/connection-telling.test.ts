import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FakeSocket, latestSocket, THIS_RUN, welcome } from './fake-socket';
import { LONGEST_RETRY } from '$lib/connection/page-connection';
import {
	A_CHAT,
	A_REPLY,
	connected,
	dropAndComeBack,
	opened,
	RecordingPage,
	SESSION_URL,
	TOLD_BEFORE
} from './recording-page';

// How far the review's telling has got when a page that dropped comes back
const TOLD_SINCE = 9;
// Where the page says its telling stands: the connection asks the page rather than counting
const PAGE_TOLD_AT = 7;

describe('going on with the telling across connections', () => {
	beforeEach(() => {
		FakeSocket.opened = [];
		vi.stubGlobal('WebSocket', FakeSocket);
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('holds the review on screen from the start, naming no place in the telling yet', () => {
		const connection = opened();

		expect(latestSocket().url).toBe(SESSION_URL);
		connection.close();
	});

	it('goes on from where the page stands once it can take what is told, on a socket of its own', () => {
		const page = new RecordingPage();
		const connection = opened();
		const holding = latestSocket();
		holding.accept();
		holding.say(welcome({ sequence: TOLD_SINCE }));
		holding.deliver(A_REPLY, TOLD_SINCE + 1);

		connection.deliverTo(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_SINCE + 1, resumed: true }));
		latestSocket().deliver(A_REPLY, TOLD_SINCE + 1);

		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${TOLD_BEFORE}`);
		expect(holding.readyState).toBe(FakeSocket.CLOSED);
		expect(page.catchUps).toBe(0);
		expect(page.heard).toEqual([A_REPLY]);
		connection.close();
	});

	it('holds the review on screen with the first socket until the one replacing it is open', () => {
		const connection = opened();
		const holding = latestSocket();
		holding.accept();

		connection.deliverTo(new RecordingPage());
		expect(holding.readyState).toBe(FakeSocket.OPEN);

		latestSocket().accept();
		expect(holding.readyState).toBe(FakeSocket.CLOSED);
		connection.close();
	});

	it('takes nothing from the socket it is replacing, however late that one speaks', () => {
		const page = new RecordingPage();
		const connection = opened();
		const holding = latestSocket();
		connection.deliverTo(page);

		holding.accept();
		holding.say(welcome({ sequence: TOLD_SINCE }));
		holding.deliver(A_REPLY, TOLD_SINCE + 1);

		expect(page.catchUps).toBe(0);
		expect(page.heard).toEqual([]);
		connection.close();
	});

	it('goes on from where the page stands at once, even while waiting to connect again', () => {
		const connection = opened();
		latestSocket().drop();

		connection.deliverTo(new RecordingPage());
		vi.advanceTimersByTime(LONGEST_RETRY);

		expect(FakeSocket.opened).toHaveLength(2);
		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${TOLD_BEFORE}`);
		connection.close();
	});

	it('hands each push over with where it stands in the telling', () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE, resumed: true }));

		latestSocket().deliver(A_REPLY, TOLD_BEFORE + 1);

		expect(page.heardAt).toEqual([{ instance: THIS_RUN, sequence: TOLD_BEFORE + 1 }]);
		connection.close();
	});

	it('comes back naming the run of the review it read and the last push the page took in', () => {
		const connection = connected();
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE, resumed: true }));
		latestSocket().deliver(A_REPLY, TOLD_BEFORE + 1);

		dropAndComeBack();

		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${TOLD_BEFORE + 1}`);
		connection.close();
	});

	it('comes back from where the page says its telling stands, not from where its socket was', () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE, resumed: true }));

		page.position = { instance: THIS_RUN, sequence: PAGE_TOLD_AT };
		dropAndComeBack();

		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${PAGE_TOLD_AT}`);
		connection.close();
	});

	it('reads on from what it was handed when the review hands over what it missed', () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE, resumed: true }));

		dropAndComeBack();
		latestSocket().say(welcome({ sequence: TOLD_SINCE, resumed: true }));
		latestSocket().deliver(A_REPLY, TOLD_BEFORE + 1);

		expect(page.catchUps).toBe(0);
		expect(page.heard).toEqual([A_REPLY]);
		connection.close();
	});

	it('catches up from where the telling goes on when even its first connection is handed nothing', () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();

		latestSocket().say(welcome({ sequence: TOLD_SINCE }));

		expect(page.caughtUpFrom).toEqual([{ instance: THIS_RUN, sequence: TOLD_SINCE }]);
		connection.close();
	});

	it('catches up when it comes back without what it missed, holding what arrives meanwhile', async () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_BEFORE, resumed: true }));

		dropAndComeBack();
		latestSocket().say(welcome({ sequence: TOLD_SINCE }));
		latestSocket().deliver(A_CHAT, TOLD_SINCE + 1);

		expect(page.catchUps).toBe(1);
		expect(page.heard).toEqual([]);

		page.finishCatchingUp();

		await vi.waitFor(() => expect(page.heard).toEqual([A_CHAT]));
		dropAndComeBack();
		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${TOLD_SINCE + 1}`);
		connection.close();
	});

	it('hands over what arrived while it caught up in the order the review told it', async () => {
		const page = new RecordingPage();
		const connection = connected(page);
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: TOLD_SINCE }));
		latestSocket().deliver(A_REPLY, TOLD_SINCE + 1);
		latestSocket().deliver(A_CHAT, TOLD_SINCE + 2);

		page.finishCatchingUp();

		await vi.waitFor(() => expect(page.heard).toEqual([A_REPLY, A_CHAT]));
		expect(page.heardAt.map((at) => at.sequence)).toEqual([TOLD_SINCE + 1, TOLD_SINCE + 2]);
		connection.close();
	});
});
