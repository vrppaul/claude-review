import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { flushSync } from 'svelte';
import { FIRST_RETRY, PageConnection } from '$lib/connection/page-connection';
import { readDraft } from '$lib/drafts/draft-storage';
import { ReviewPage } from '$lib/page/review-page.svelte';
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import { diffResponse, REVIEW_TITLE, reviewResponse } from './diff';
import { fakeServer, NEW_READER, SERVER_ERROR, takingStoryAskings, type FakeServer } from './fake-server';
import { FakeSocket, latestSocket, REVIEW_IDENTITY, THIS_RUN, welcome } from './fake-socket';
import { lineAnchor } from '$lib/anchors/line';
import type { FollowRequest, HeldThread, ReaderSettings, SaidInPanel, ServerPush } from '$lib/types';
import { newComment } from './new-comment';
import { chatPush, NO_WORK, pushedAt } from './pushes';
import { leavePage, openReview } from './review';
import { settled } from './settled';
import { STOPPED, storyHeld, storyResponse, TAKEN } from './story';

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

// A thread the review holds, as a page in another browser said it
const A_HELD_THREAD: HeldThread = {
	thread_id: 'comment-1',
	anchor: lineAnchor('a.py', 'new', 1, 1, ['x = 1']),
	severity: 'question',
	body: 'Written in another browser',
	images: [],
	turns: [{ turn_id: 'turn-3', author: 'author', body: 'Answered', round: 2, images: [] }],
	raised_by: 'reader',
	resolved: false
};
// A thread the agent raised, as the review holds it
const A_RAISED_THREAD: HeldThread = {
	thread_id: 'raised-1',
	anchor: lineAnchor('a.py', 'new', 2, 2, ['y = 2']),
	severity: 'note',
	body: 'Look here',
	images: [],
	turns: [],
	raised_by: 'author',
	resolved: false
};

// How long before or after the test runs something was said in the panel
const A_MINUTE = 60_000;
const NOW = Date.now();
// A message the reader sent from another browser, before this page opened
const A_MESSAGE_SENT_ELSEWHERE: SaidInPanel = {
	said_id: 'panel-1',
	message_id: 'panel-1',
	author: 'reader',
	body: 'Run the tests and say what fails.',
	at: NOW - A_MINUTE,
	images: ['shot.png'],
	threads: ['comment-1'],
	files: [],
	taken_back: false
};
// The agent's answer to it, said before any page was open
const AN_ANSWER_BEFORE_ANY_PAGE: SaidInPanel = {
	said_id: 'answer-3f2a',
	message_id: 'panel-1',
	author: 'author',
	body: 'One failed; fixed.',
	at: NOW - A_MINUTE / 2,
	images: [],
	threads: [],
	files: ['a.py'],
	taken_back: false
};
// What the agent said once the test had begun: after any note a page made of its own
const AN_ANSWER_LATER: SaidInPanel = {
	...AN_ANSWER_BEFORE_ANY_PAGE,
	said_id: 'answer-9c1d',
	body: 'All green.',
	at: NOW + A_MINUTE
};

/** What the panel draws, turn by turn: who said it, and what. */
function panelOf(page: ReviewPage): string[] {
	return openedReview(page).conversation.turns.map((turn) => `${turn.author}: ${turn.body}`);
}

/** A page on the review's socket, let go of once the test is over. */
function newPage(closeTab: () => void = () => undefined): ReviewPage {
	const page = new ReviewPage(new PageConnection(SESSION_URL), closeTab);
	openedPages.push(page);
	return page;
}

/** A page opened on its review and welcomed on its socket, with a thread written in it. */
async function openWithAThread(closeTab: () => void = () => undefined): Promise<ReviewPage> {
	const page = newPage(closeTab);
	await page.open();
	latestSocket().accept();
	latestSocket().say(welcome({ resumed: true }));
	openedReview(page).threads.add(newComment({ body: 'not sent yet' }));
	flushSync();
	return page;
}

/** Leave the socket to come back on its own, for longer than it ever waits, and say how many it opened meanwhile. */
function socketsOpenedAfterLongWait(): number {
	const opened = FakeSocket.opened.length;
	vi.useFakeTimers();
	latestSocket().drop();
	vi.advanceTimersByTime(LONGER_THAN_ANY_RETRY);
	vi.useRealTimers();
	return FakeSocket.opened.length - opened;
}

/** Whether the browser would ask the reader before the tab leaves the page now. */
function asksBeforeLeaving(): boolean {
	const leaving = new Event('beforeunload', { cancelable: true });
	window.dispatchEvent(leaving);
	return leaving.defaultPrevented;
}

/** The review an open page holds. */
function openedReview(page: ReviewPage): Review {
	if (page.state.kind !== 'open') throw new Error(`The page is ${page.state.kind}`);
	return page.state.review;
}

/** A server with a review to open, a reader it knows nothing about yet, and threads that stay where they are. */
function serving(): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/settings', { record: NEW_READER, stored: true });
	server.answer('GET /api/review', reviewResponse());
	server.answer('GET /api/diff', diffResponse());
	server.answer('GET /api/threads', { threads: [] });
	server.answer('GET /api/conversation', { said: [] });
	server.answer('GET /api/story', storyResponse());
	server.answer('GET /api/guide', { record: { seen_release: '1.5.0' }, stored: true });
	server.answerWith('POST /api/anchors/follow', (request) => request.body as FollowRequest);
	return server;
}

/** The same server, for a reader who turned stories on in some review. */
function servingAReaderWithStoriesOn(): FakeServer {
	const server = serving();
	server.answer('GET /api/settings', { record: { ...NEW_READER, stories: true }, stored: true });
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

	it('opens on the story the review holds, where the agent has told one', async () => {
		const told = storyHeld({ title: 'Told before the page opened' });
		serving().answer('GET /api/story', storyResponse({ held: told }));
		const page = newPage();

		await page.open();

		expect(openedReview(page).story.held).toEqual(told);
	});

	it('opens on how the asking for a story stands, where the reader asked for one before it opened', async () => {
		serving().answer('GET /api/review', reviewResponse({ story_asking: TAKEN }));
		const page = newPage();

		await page.open();

		expect(openedReview(page).story.wait).toEqual({ kind: 'writing', asking: TAKEN });
	});

	it('asks the agent for a story as it opens, where the reader turned stories on and none is asked for', async () => {
		const server = takingStoryAskings(servingAReaderWithStoriesOn());
		const page = newPage();

		await page.open();
		await settled();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it.each([
		{ where: 'the review holds a story', facts: reviewResponse(), story: storyResponse({ held: storyHeld() }) },
		{
			where: 'one is awaited already, asked for from another page',
			facts: reviewResponse({ story_asking: TAKEN }),
			story: storyResponse()
		},
		{
			where: 'the reader stopped the one asked for, before a reload',
			facts: reviewResponse({ story_asking: STOPPED }),
			story: storyResponse()
		}
	])('asks for no story as it opens where $where', async ({ facts, story }) => {
		const server = takingStoryAskings(servingAReaderWithStoriesOn());
		server.answer('GET /api/review', facts);
		server.answer('GET /api/story', story);
		const page = newPage();

		await page.open();
		await settled();

		expect(server.requestsTo('POST /api/story/request')).toEqual([]);
	});

	it('asks for no story as it opens where the reader left stories off', async () => {
		const server = takingStoryAskings(serving());
		const page = newPage();

		await page.open();
		await settled();

		expect(server.requestsTo('POST /api/story/request')).toEqual([]);
	});

	it('asks for no story of a review that takes none, and holds none', async () => {
		const server = serving();
		server.answer('GET /api/review', reviewResponse({ takes_a_story: false }));
		const page = newPage();

		await page.open();

		expect(server.requestsTo('GET /api/story')).toEqual([]);
		expect(openedReview(page).story.held).toBeNull();
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

		expect(latestSocket().url).toBe(
			`${SESSION_URL}?identity=${REVIEW_IDENTITY}&instance=${THIS_RUN}&after=${DRAFT_LEFT_AT}`
		);
		expect(openedReview(page).threads.all[0].turns.at(-1)?.body).toBe('Because.');
	});

	it('takes in once a push its socket handed over twice', async () => {
		serving();
		const page = newPage();
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		const chat: ServerPush = chatPush('Done.');
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

	it('takes in every answer said while it read the review again, each in its turn', async () => {
		const server = serving();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		const page = newPage();
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		const facts = server.hold('GET /api/review');

		vi.useFakeTimers();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		vi.useRealTimers();
		latestSocket().accept();
		latestSocket().say(welcome({ sequence: FACTS_READ_AT }));
		await vi.waitFor(() => expect(facts.requests).toHaveLength(1));
		latestSocket().deliver(chatPush('first'), FACTS_READ_AT + 1);
		latestSocket().deliver(chatPush('second'), FACTS_READ_AT + 2);
		facts.answer(0, reviewResponse({ sequence: FACTS_READ_AT }));

		const review = openedReview(page);
		await vi.waitFor(() => expect(review.telling.heard.sequence).toBe(FACTS_READ_AT + 2));
		expect(review.conversation.turns.map((turn) => turn.body).slice(-2)).toEqual(['first', 'second']);
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
		await vi.waitFor(() => expect(latestSocket().closedByThePage).toBe(true));
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

	it('says it cannot reach its review while its socket is down, and that it can once welcomed back', async () => {
		serving();
		const page = await openWithAThread();
		const review = openedReview(page);
		expect(review.link.state).toBe('connected');

		vi.useFakeTimers();
		latestSocket().drop();
		const whileDown = review.link.state;
		vi.advanceTimersByTime(FIRST_RETRY);
		vi.useRealTimers();
		latestSocket().accept();
		const openButNotWelcomed = review.link.state;
		latestSocket().say(welcome({ resumed: true }));

		expect(whileDown).toBe('reconnecting');
		expect(openButNotWelcomed).toBe('reconnecting');
		expect(review.link.state).toBe('connected');
	});

	it('lets go of a review stopped under it, keeping what was not sent for when it is opened again', async () => {
		serving();
		const closeTab = vi.fn();
		const page = await openWithAThread(closeTab);

		latestSocket().deliver({ type: 'ended', finished: false }, 1);
		await settled();

		expect(openedReview(page).link.ending).toBe('stopped');
		expect(socketsOpenedAfterLongWait()).toBe(0);
		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft?.threads.map((thread) => thread.body)).toEqual([
			'not sent yet'
		]);
		expect(closeTab).not.toHaveBeenCalled();
	});

	it('lets go of a review sent for good from another tab, forgetting its draft, and leaves its own tab open', async () => {
		serving();
		const closeTab = vi.fn();
		const page = await openWithAThread(closeTab);

		latestSocket().deliver({ type: 'ended', finished: true }, 1);
		await settled();

		expect(openedReview(page).link.ending).toBe('finished');
		expect(socketsOpenedAfterLongWait()).toBe(0);
		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft).toBeNull();
		expect(closeTab).not.toHaveBeenCalled();
	});

	it('hands another review reached on its port nothing of its own, and says its own is over', async () => {
		serving();
		const page = await openWithAThread();

		vi.useFakeTimers();
		latestSocket().drop();
		vi.advanceTimersByTime(FIRST_RETRY);
		vi.useRealTimers();
		const elsewhere = latestSocket();
		elsewhere.accept();
		elsewhere.say(welcome({ identity: 'the-next-review-on-this-port', sequence: 0 }));
		await settled();

		expect(elsewhere.said).toEqual([]);
		expect(openedReview(page).link.ending).toBe('replaced');
		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft?.threads).toHaveLength(1);
	});

	it('takes the threads the review holds as its own when this browser kept no draft of it', async () => {
		serving().answer('GET /api/threads', { threads: [A_HELD_THREAD, A_RAISED_THREAD] });
		const page = newPage();

		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));
		flushSync();

		const review = openedReview(page);
		expect(review.threads.all.map((thread) => thread.id)).toEqual(['comment-1', 'raised-1']);
		expect(review.threads.unsent.map((thread) => thread.id)).toEqual(['comment-1']);
		expect(latestSocket().said).toMatchObject([{ threads: [{ thread_id: 'comment-1' }, { thread_id: 'raised-1' }] }]);
	});

	it('writes its next comment under an id none of the threads it took in has', async () => {
		serving().answer('GET /api/threads', { threads: [A_HELD_THREAD] });
		const page = newPage();
		await page.open();

		const added = openedReview(page).threads.add(newComment({ body: 'mine' }));

		expect(added).not.toBe('comment-1');
	});

	it('takes in once a thread the agent raised as the page opened, held and pushed both', async () => {
		serving().answer('GET /api/threads', { threads: [A_RAISED_THREAD] });
		const page = newPage();
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));

		const { thread_id, anchor, body, severity } = A_RAISED_THREAD;
		latestSocket().deliver({ type: 'point', thread_id, anchor, body, severity }, 1);

		expect(openedReview(page).threads.all.map((thread) => thread.id)).toEqual(['raised-1']);
	});

	it('keeps to its own draft rather than the threads the review holds', async () => {
		const server = serving();
		server.answer('GET /api/threads', { threads: [A_HELD_THREAD] });
		openReview().threads.add(newComment({ body: 'written in this browser' }));
		leavePage();
		server.answer('POST /api/anchors/follow', { anchors: [newComment().anchor] });
		const page = newPage();

		await page.open();

		expect(openedReview(page).threads.all.map((thread) => thread.body)).toEqual(['written in this browser']);
	});

	it('draws what was said in the panel before it opened, as a browser with no draft of it opens, before any push', async () => {
		serving().answer('GET /api/conversation', { said: [A_MESSAGE_SENT_ELSEWHERE, AN_ANSWER_BEFORE_ANY_PAGE] });
		const page = newPage();

		await page.open();

		expect(panelOf(page)).toEqual(['reader: Run the tests and say what fails.', 'author: One failed; fixed.']);
		expect(openedReview(page).conversation.turns).toMatchObject([
			{ id: 'panel-1', images: ['shot.png'], threads: ['comment-1'] },
			{ id: 'answer-3f2a', answers: 'panel-1', files: ['a.py'] }
		]);
	});

	it('reads what was said in the panel only once it knows how far the telling had got, so nothing said meanwhile is missed', async () => {
		const server = serving();
		const facts = server.hold('GET /api/review');
		const page = newPage();

		const opening = page.open();
		await vi.waitFor(() => expect(facts.requests).toHaveLength(1));

		expect(server.requestsTo('GET /api/conversation')).toEqual([]);
		facts.answer(0, reviewResponse());
		await opening;
		expect(server.requestsTo('GET /api/conversation')).toHaveLength(1);
	});

	it('draws each thing said once on a reload, with what only its draft holds, in the order it all came', async () => {
		const server = serving();
		openReview({ said: [A_MESSAGE_SENT_ELSEWHERE, AN_ANSWER_BEFORE_ANY_PAGE] }).conversation.note(
			'Took the diff again'
		);
		leavePage();
		server.answer('GET /api/conversation', {
			said: [A_MESSAGE_SENT_ELSEWHERE, AN_ANSWER_BEFORE_ANY_PAGE, AN_ANSWER_LATER]
		});
		const page = newPage();

		await page.open();

		expect(panelOf(page)).toEqual([
			'reader: Run the tests and say what fails.',
			'author: One failed; fixed.',
			'event: Took the diff again',
			'author: All green.'
		]);
	});

	it('draws a message as the review holds it rather than as its draft kept it: taken back in another window since', async () => {
		const server = serving();
		openReview({ said: [A_MESSAGE_SENT_ELSEWHERE] });
		leavePage();
		server.answer('GET /api/conversation', { said: [{ ...A_MESSAGE_SENT_ELSEWHERE, taken_back: true }] });
		const page = newPage();

		await page.open();

		expect(openedReview(page).conversation.turns).toMatchObject([{ id: 'panel-1', cancelled: true }]);
	});

	it('takes in once what the agent said as the page opened, held and pushed both, and counts it as nothing new', async () => {
		serving().answer('GET /api/conversation', { said: [AN_ANSWER_BEFORE_ANY_PAGE] });
		const page = newPage();
		await page.open();
		latestSocket().accept();
		latestSocket().say(welcome({ resumed: true }));

		const { said_id, message_id, body, files } = AN_ANSWER_BEFORE_ANY_PAGE;
		latestSocket().deliver({ type: 'chat', said_id, message_id, body, files }, 1);

		expect(panelOf(page)).toEqual(['author: One failed; fixed.']);
		// Nor is it a new answer for the shut panel to count
		expect(openedReview(page).layout.agentPanel.unread).toBe(0);
	});

	it('asks before the tab leaves the review with something unsent in it, and only then', async () => {
		serving();
		const page = newPage();
		await page.open();
		const review = openedReview(page);

		const withNothing = asksBeforeLeaving();
		review.submission.setBody('Mostly fine');
		const withASummary = asksBeforeLeaving();
		page.close();
		const onceLetGo = asksBeforeLeaving();

		expect([withNothing, withASummary, onceLetGo]).toEqual([false, true, false]);
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

/** Show the tab again, as the browser does when the reader comes back to it from another. */
function showTabAgain(): void {
	document.dispatchEvent(new Event('visibilitychange'));
}

/** The settings another tab, of this review or another, left the reader with meanwhile. */
function changedElsewhere(server: FakeServer, settings: Partial<ReaderSettings>): void {
	server.answer('GET /api/settings', { record: { ...NEW_READER, ...settings }, stored: true });
}

describe('the tab shown again', () => {
	beforeEach(() => {
		FakeSocket.opened = [];
		vi.stubGlobal('WebSocket', FakeSocket);
	});

	afterEach(() => {
		for (const page of openedPages.splice(0)) page.close();
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});

	it("reads the reader's settings again: what another tab chose meanwhile applies here", async () => {
		const server = serving();
		const page = newPage();
		await page.open();
		changedElsewhere(server, { diff_layout: 'split' });

		showTabAgain();
		await settled();

		expect(openedReview(page).settings.current.diff_layout).toBe('split');
	});

	it('takes the diff again where another tab changed whether whitespace counts', async () => {
		const server = serving();
		const page = newPage();
		await page.open();
		changedElsewhere(server, { ignore_whitespace: true });

		showTabAgain();
		await settled();

		expect(server.requestsTo('GET /api/diff').map((request) => request.query)).toEqual([
			{},
			{ ignore_whitespace: 'true' }
		]);
	});

	it('takes the diff no more where whether whitespace counts is as it was, whatever else another tab changed', async () => {
		const server = serving();
		const page = newPage();
		await page.open();
		changedElsewhere(server, { diff_layout: 'split' });

		showTabAgain();
		await settled();

		expect(server.requestsTo('GET /api/diff')).toHaveLength(1);
	});

	it('asks the agent for a story where another tab turned stories on', async () => {
		const server = takingStoryAskings(serving());
		const page = newPage();
		await page.open();
		changedElsewhere(server, { stories: true });

		showTabAgain();
		await settled();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('leaves the tab as it was where the settings cannot be read', async () => {
		// Stories on, and the asking as the page opened refused: a tab that went on would ask again
		const server = servingAReaderWithStoriesOn();
		server.refuse('POST /api/story/request', SERVER_ERROR);
		const page = newPage();
		await page.open();
		await settled();
		server.refuse('GET /api/settings', SERVER_ERROR);

		showTabAgain();
		await settled();

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('reads nothing as the tab is hidden', async () => {
		const server = serving();
		const page = newPage();
		await page.open();
		vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');

		showTabAgain();
		await settled();

		expect(server.requestsTo('GET /api/settings')).toHaveLength(1);
	});

	it('reads nothing once the page has let its review go', async () => {
		const server = serving();
		const page = newPage();
		await page.open();
		page.close();

		showTabAgain();
		await settled();

		expect(server.requestsTo('GET /api/settings')).toHaveLength(1);
	});
});
