import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FIRST_RETRY, PageConnection } from '$lib/connection/page-connection';
import { ReviewPage } from '$lib/page/review-page.svelte';
import { diffResponse, reviewResponse } from './diff';
import { fakeServer, NEW_READER, SERVER_ERROR, type FakeServer } from './fake-server';
import { FakeSocket, latestSocket, welcome } from './fake-socket';
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

	it('lands an answer pushed while it opens in the thread the draft brings back', async () => {
		serving();
		// A thread written before the reload, kept in the draft
		const id = openReview().threads.add(newComment({ body: 'Why?' }));
		// And then the reload
		leavePage();
		const page = new ReviewPage(new PageConnection(SESSION_URL));

		const opening = page.open();
		latestSocket().accept();
		latestSocket().say(welcome());
		latestSocket().deliver({ type: 'reply', thread_id: id, question_id: null, body: 'Because.' }, 1);
		await opening;

		if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
		expect(page.state.review.threads.all[0].turns.at(-1)?.body).toBe('Because.');
	});

	it('reads the review again when its socket comes back without what it missed', async () => {
		const server = serving();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		const page = new ReviewPage(new PageConnection(SESSION_URL));
		const opening = page.open();
		latestSocket().accept();
		latestSocket().say(welcome());
		await opening;
		server.answer('GET /api/review', reviewResponse({ round: 4 }));

		vi.useFakeTimers();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		vi.useRealTimers();
		latestSocket().accept();
		latestSocket().say(welcome());

		if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
		const { review } = page.state;
		await vi.waitFor(() => expect(review.rounds.current).toBe(4));
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
