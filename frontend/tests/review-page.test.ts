import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FIRST_RETRY, PageConnection } from '$lib/connection/page-connection';
import { ReviewPage } from '$lib/page/review-page.svelte';
import { diffResponse, reviewResponse } from './diff';
import { fakeServer, NEW_READER, SERVER_ERROR, type FakeServer } from './fake-server';
import { FakeSocket, latestSocket, THIS_RUN, welcome } from './fake-socket';
import type { ServerPush } from '$lib/types';
import { newComment } from './new-comment';
import { leavePage, openReview } from './review';

const SESSION_URL = 'ws://review.test/api/session';

/** A server with a review to open, and a reader it knows nothing about yet. */
function serving(): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/settings', { record: NEW_READER, stored: true });
	server.answer('GET /api/review', reviewResponse());
	server.answer('GET /api/diff', diffResponse());
	server.answer('GET /api/guide', { record: { seen_release: '1.5.0' }, stored: true });
	return server;
}

describe('opening the page', () => {
	beforeEach(() => {
		FakeSocket.opened = [];
		vi.stubGlobal('WebSocket', FakeSocket);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('holds its socket while the review is still being read, so a slow read does not end it', async () => {
		const server = serving();
		const facts = server.hold('GET /api/review');
		const page = new ReviewPage(new PageConnection(SESSION_URL));

		const opening = page.open();
		await vi.waitFor(() => expect(facts.requests).toHaveLength(1));

		expect(page.state.kind).toBe('opening');
		expect(FakeSocket.opened.map((socket) => socket.url)).toEqual([SESSION_URL]);
		facts.answer(0, reviewResponse());
		await opening;
	});

	it('is handed what was said while it reloaded, into the thread the draft brings back', async () => {
		serving();
		// A thread written before the reload, kept in the draft
		const id = openReview().threads.add(newComment({ body: 'Why?' }));
		// And then the reload
		leavePage();
		const page = new ReviewPage(new PageConnection(SESSION_URL));

		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		latestSocket().deliver({ type: 'reply', thread_id: id, question_id: null, body: 'Because.' }, 1);

		if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=0`);
		expect(page.state.review.threads.all[0].turns.at(-1)?.body).toBe('Because.');
	});

	it('takes in once what another tab took in first', async () => {
		serving();
		const page = new ReviewPage(new PageConnection(SESSION_URL));
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
		const { review } = page.state;
		const chat: ServerPush = { type: 'chat', message_id: null, body: 'Done.', files: [] };
		latestSocket().deliver(chat, 1);

		latestSocket().deliver(chat, 1);

		expect(review.conversation.turns.filter((turn) => turn.body === 'Done.')).toHaveLength(1);
	});

	it('reads the review again when its socket comes back without what it missed', async () => {
		const server = serving();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		const page = new ReviewPage(new PageConnection(SESSION_URL));
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		server.answer('GET /api/review', reviewResponse({ round: 4 }));

		vi.useFakeTimers();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		vi.useRealTimers();
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: 5 }));

		if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
		const { review } = page.state;
		await vi.waitFor(() => expect(review.rounds.current).toBe(4));
		expect(review.telling.position).toEqual({ instance: THIS_RUN, sequence: 5 });
	});

	it('says why when the review cannot be opened', async () => {
		serving().fail('GET /api/review', SERVER_ERROR);
		const page = new ReviewPage(new PageConnection(SESSION_URL));

		await page.open();

		expect(page.state).toEqual({
			kind: 'failed',
			reason: `Could not open the review: ${SERVER_ERROR}`
		});
	});
});
