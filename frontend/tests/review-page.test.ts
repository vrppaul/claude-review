import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FIRST_RETRY, PageConnection } from '$lib/connection/page-connection';
import { ReviewPage } from '$lib/page/review-page.svelte';
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import { diffResponse, reviewResponse } from './diff';
import { fakeServer, NEW_READER, SERVER_ERROR, type FakeServer } from './fake-server';
import { FakeSocket, latestSocket, THIS_RUN, welcome } from './fake-socket';
import type { ServerPush } from '$lib/types';
import { newComment } from './new-comment';
import { NO_WORK, pushedAt } from './pushes';
import { leavePage, openReview } from './review';
import { settled } from './settled';

const SESSION_URL = 'ws://review.test/api/session';
// How far the review's telling had got when the page read its facts
const FACTS_READ_AT = 5;
// How far the draft a reloaded page opens from had got
const DRAFT_LEFT_AT = 2;
// Where a thread was written, and where the diff the page opens on has it now
const WRITTEN_AT_LINE = 3;
const NOW_AT_LINE = 7;
// Longer than a page waits before it tries its socket again, however often it has
const LONGER_THAN_ANY_RETRY = 60_000;

// The pages a test opened: each is let go once the test is over, so none
// keeps its draft into the next
const openedPages: ReviewPage[] = [];

/** A page on the review's socket, let go of once the test is over. */
function newPage(closeTab: () => void = () => undefined): ReviewPage {
	const page = new ReviewPage(new PageConnection(SESSION_URL), closeTab);
	openedPages.push(page);
	return page;
}

/** The review an open page holds. */
function openedReview(page: ReviewPage): Review {
	if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
	return page.state.review;
}

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
		for (const page of openedPages.splice(0)) page.close();
		vi.unstubAllGlobals();
	});

	it('holds its socket while the review is still being read, so a slow read does not end it', async () => {
		const server = serving();
		const facts = server.hold('GET /api/review');
		const page = newPage();

		const opening = page.open();
		await vi.waitFor(() => expect(facts.requests).toHaveLength(1));

		expect(page.state.kind).toBe('opening');
		expect(FakeSocket.opened.map((socket) => socket.url)).toEqual([SESSION_URL]);
		facts.answer(0, reviewResponse());
		await opening;
	});

	it('reads the diff only once it knows how far the telling had got, so the diff holds all of it', async () => {
		const server = serving();
		const facts = server.hold('GET /api/review');
		const page = newPage();

		const opening = page.open();
		await vi.waitFor(() => expect(facts.requests).toHaveLength(1));

		expect(server.requestsTo('GET /api/diff')).toEqual([]);
		facts.answer(0, reviewResponse());
		await opening;
		expect(server.requestsTo('GET /api/diff')).toHaveLength(1);
	});

	it('is handed what was said while it reloaded, into the thread the draft brings back', async () => {
		const server = serving();
		// A thread written before the reload, and pushes taken in up to the second
		const before = openReview();
		const id = before.threads.add(newComment({ body: 'Why?' }));
		takePush(before, NO_WORK, pushedAt(1));
		takePush(before, NO_WORK, pushedAt(DRAFT_LEFT_AT));
		// And then the reload, while the review's telling goes on to the fifth
		leavePage();
		server.answer('GET /api/review', reviewResponse({ sequence: FACTS_READ_AT }));
		server.answer('POST /api/anchors/follow', { anchors: [before.threads.all[0].anchor] });
		const page = newPage();

		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: FACTS_READ_AT, resumed: true }));
		latestSocket().deliver({ type: 'reply', thread_id: id, question_id: null, body: 'Because.' }, DRAFT_LEFT_AT + 1);

		expect(latestSocket().url).toBe(`${SESSION_URL}?instance=${THIS_RUN}&after=${DRAFT_LEFT_AT}`);
		expect(openedReview(page).threads.all[0].turns.at(-1)?.body).toBe('Because.');
	});

	it('takes in once a push its socket handed over twice', async () => {
		serving();
		const page = newPage();
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		const chat: ServerPush = { type: 'chat', message_id: null, body: 'Done.', files: [] };
		latestSocket().deliver(chat, 1);

		latestSocket().deliver(chat, 1);

		expect(openedReview(page).conversation.turns.filter((turn) => turn.body === 'Done.')).toHaveLength(1);
	});

	it('reads the review again when its socket comes back without what it missed', async () => {
		const server = serving();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		const page = newPage();
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

		const review = openedReview(page);
		await vi.waitFor(() => expect(review.rounds.current).toBe(4));
		expect(review.telling.heard).toEqual({ instance: THIS_RUN, sequence: 5 });
	});

	it('follows the threads its draft brought back onto the diff it opened on', async () => {
		const server = serving();
		// Written before a reload that came while a retake was still moving it
		const before = openReview();
		before.threads.add(newComment({ startLine: WRITTEN_AT_LINE, quote: ['x = 1'] }));
		leavePage();
		const moved = { ...before.threads.all[0].anchor, start_line: NOW_AT_LINE, end_line: NOW_AT_LINE };
		server.answer('POST /api/anchors/follow', { anchors: [moved] });
		const page = newPage();

		await page.open();

		const review = openedReview(page);
		await vi.waitFor(() => expect(review.threads.all[0].anchor.start_line).toBe(NOW_AT_LINE));
		expect(review.conversation.turns.at(-1)?.body).toContain('1 thread followed its lines');
	});

	it('says nothing in the panel when the threads its draft brought back are where they were', async () => {
		const server = serving();
		const before = openReview();
		before.threads.add(newComment({ body: 'Why?' }));
		leavePage();
		server.answer('POST /api/anchors/follow', { anchors: [before.threads.all[0].anchor] });
		const page = newPage();

		await page.open();
		await settled();

		expect(server.requestsTo('POST /api/anchors/follow')).toHaveLength(1);
		expect(openedReview(page).conversation.turns).toEqual([]);
	});

	it('lets go of its socket once the review is sent for good, so the next review on the port never hears of it', async () => {
		serving().answer('POST /api/submit', { markdown: '## Review', comment_count: 0, round: 1, ended: true });
		const page = newPage();
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));

		await openedReview(page).submission.submit(true);
		await vi.waitFor(() => expect(latestSocket().readyState).toBe(FakeSocket.CLOSED));
		const opened = FakeSocket.opened.length;
		vi.useFakeTimers();
		// The review's server goes, and another comes up on the same port
		latestSocket().drop();
		vi.advanceTimersByTime(LONGER_THAN_ANY_RETRY);
		vi.useRealTimers();

		expect(FakeSocket.opened).toHaveLength(opened);
	});

	it('shuts its tab once the review is sent for good, and not for a round', async () => {
		const server = serving();
		server.answer('POST /api/submit', { markdown: '## Round', comment_count: 0, round: 1, ended: false });
		const closeTab = vi.fn();
		const page = newPage(closeTab);
		await page.open();

		await openedReview(page).submission.submit(false);
		await settled();
		expect(closeTab).not.toHaveBeenCalled();

		server.answer('POST /api/submit', { markdown: '## Review', comment_count: 0, round: 2, ended: true });
		await openedReview(page).submission.submit(true);
		await settled();
		expect(closeTab).toHaveBeenCalledOnce();
	});

	it('says why when the review cannot be opened', async () => {
		serving().fail('GET /api/review', SERVER_ERROR);
		const page = newPage();

		await page.open();

		expect(page.state).toEqual({
			kind: 'failed',
			reason: `Could not open the review: ${SERVER_ERROR}`
		});
	});
});
