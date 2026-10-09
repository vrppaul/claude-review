import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import DiffNotice from '$lib/components/DiffNotice.svelte';
import { catchUp } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import type { ServerPush, SessionHello } from '$lib/types';
import { work } from './agent-work';
import { contextLine, diffFile, diffResponse, hunk, reviewResponse } from './diff';
import { fakeServer, SERVER_ERROR, type FakeServer } from './fake-server';
import { THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { inReview, openReview } from './review';
import { pushedAt, told } from './pushes';

/** A file whose first line the change left alone. */
function untouched(path: string) {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

/** Let a push whose work goes on after it is taken — a retake — finish it. */
function settled(): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve));
}

let review: Review;

beforeEach(() => {
	review = openReview({ files: [untouched('a.py'), untouched('b.py')] });
});

describe('what the server pushes, taken in', () => {
	it('puts an answer under the thread it answers, unread', () => {
		const id = review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));

		told(review, { type: 'reply', thread_id: id, question_id: null, body: 'Because.' });

		expect(review.threads.all[0].turns.at(-1)?.body).toBe('Because.');
		expect(review.threads.unread.map((thread) => thread.id)).toEqual([id]);
	});

	it('offers the panel when an agent turns up, and stops offering rounds when it goes', () => {
		told(review, { type: 'answerer', attached: true });
		expect(review.answerer.attached).toBe(true);
		expect(review.layout.agentPanel.open).toBe(true);

		told(review, { type: 'answerer', attached: false });
		expect(review.answerer.attached).toBe(false);
	});

	it('counts an answer in the panel while the panel is shut', () => {
		review.layout.agentPanel.setOpen(false);

		told(review, { type: 'chat', message_id: null, body: 'Done.', files: [] });

		expect(review.conversation.turns.at(-1)?.body).toBe('Done.');
		expect(review.layout.agentPanel.unread).toBe(1);
	});

	it('says the tree moved, the moment it does, without touching the diff', () => {
		const { getByTestId } = render(DiffNotice, inReview(review));

		told(review, { type: 'changed', moved_count: 3 });
		flushSync();

		expect(getByTestId('tree-moved').textContent).toContain('3');
		expect(review.diff.files.map((file) => file.path)).toEqual(['a.py', 'b.py']);
	});

	it('moves on to the round the server began, never back', () => {
		told(review, { type: 'round', number: 3 });
		told(review, { type: 'round', number: 2 });

		expect(review.rounds.current).toBe(3);
	});

	it('puts a thread the agent raised on the diff, and says so in the panel', () => {
		const anchor = newComment({ file: 'a.py' }).anchor;

		told(review, { type: 'point', thread_id: 'raised-1', anchor, body: 'Look', severity: 'note' });

		expect(review.threads.all[0].raised_by).toBe('author');
		expect(review.conversation.turns.at(-1)?.threads).toEqual(['raised-1']);
	});

	it("counts the review's files after a retake, not those of a narrower base on screen", async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		// A narrower base shows one file of the review's three
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], base_key: 'round:1' }));
		const retake: ServerPush = { type: 'diff', file_count: 3, changes: null };

		told(review, retake);
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe('diff retaken · 3 files');
	});

	it('takes one retake in at a time, so threads never follow onto a diff older than the one shown', async () => {
		const server = fakeServer();
		const follows = server.hold('POST /api/anchors/follow');
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')] }));
		const retake: ServerPush = { type: 'diff', file_count: 1, changes: null };

		told(review, retake);
		told(review, retake);
		await settled();
		expect(follows.requests).toHaveLength(1);

		follows.answer(0, { anchors: [] });
		await vi.waitFor(() => expect(follows.requests).toHaveLength(2));
		follows.answer(1, { anchors: [] });
	});

	it('says the tree moved again when it moved while the retaken diff was on its way', async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], moved: 2 }));

		told(review, { type: 'changed', moved_count: 1 });
		told(review, { type: 'diff', file_count: 1, changes: null });
		await settled();

		expect(review.diff.treeMoved.count).toBe(2);
	});

	it('says one file as one', async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')] }));

		told(review, { type: 'diff', file_count: 1, changes: null });
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe('diff retaken · 1 file');
	});
});

// Where the telling goes on after what could not be handed over
const GOES_ON_FROM = { instance: THIS_RUN, sequence: 0 };

/** A server the page can catch up from: the review as it now stands, and its threads where they were. */
function caughtUpFrom(): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/review', reviewResponse());
	server.answer('POST /api/anchors/follow', { anchors: [] });
	server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py'), untouched('b.py')] }));
	return server;
}

describe('catching up on what the server could not hand over again', () => {
	it('learns again where the review stands: the round, whoever answers, and its work', async () => {
		const status = { model: 'opus-5', context: '53% of 1M', at: Date.now() };
		const underWay = work();
		caughtUpFrom().answer(
			'GET /api/review',
			reviewResponse({ round: 3, answerer_attached: true, agent: status, work: underWay })
		);

		await catchUp(review, GOES_ON_FROM);

		expect(review.rounds.current).toBe(3);
		expect(review.answerer.attached).toBe(true);
		expect(review.answerer.status).toEqual(status);
		expect(review.answerer.work).toEqual(underWay);
		expect(review.layout.agentPanel.open).toBe(true);
	});

	it('follows the threads onto the diff as it stands, in case a retake was among what was missed', async () => {
		const id = review.threads.add(newComment({ file: 'a.py', startLine: 1, quote: ['x'] }));
		const moved = { ...review.threads.all[0].anchor, start_line: 2, end_line: 2 };
		caughtUpFrom().answer('POST /api/anchors/follow', { anchors: [moved] });

		await catchUp(review, GOES_ON_FROM);

		expect(review.threads.all.find((thread) => thread.id === id)?.anchor.start_line).toBe(2);
		expect(review.conversation.turns.at(-1)?.body).toContain('1 thread followed its lines');
	});

	it('says in the panel that what was said meanwhile may be missing, and leaves the ticks alone', async () => {
		caughtUpFrom();
		review.reading.setViewed('a.py', true);

		await catchUp(review, GOES_ON_FROM);

		expect(review.conversation.turns.at(-1)?.body).toMatch(/anything said meanwhile may be missing/);
		expect(review.reading.isViewed('a.py')).toBe(true);
	});

	it('says so when the review cannot be read again', async () => {
		caughtUpFrom().fail('GET /api/review', SERVER_ERROR);

		await catchUp(review, GOES_ON_FROM);

		expect(review.conversation.turns.at(-1)?.body).toMatch(/could not be read again/);
	});
});

describe('what the page tells the server it holds', () => {
	it('is the round it has reached and every thread, said again whenever either changes', () => {
		const said: SessionHello[] = [];
		const stop = review.tellServerThrough({ greet: (hello) => said.push(hello) });
		flushSync();

		review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
		review.rounds.reach(2);
		flushSync();

		expect(said.at(0)).toEqual({ round: 1, threads: [] });
		expect(said.at(-1)?.round).toBe(2);
		expect(said.at(-1)?.threads?.map((thread) => thread.body)).toEqual(['Why?']);
		stop();
	});

	it('is not said again for how the page reads, which the server has no use for', () => {
		const id = review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
		review.threads.receiveReply(id, 'Because.', null, pushedAt(1));
		const said: SessionHello[] = [];
		const stop = review.tellServerThrough({ greet: (hello) => said.push(hello) });
		flushSync();

		review.reading.toggleFolded('a.py');
		review.threads.reading.setFolded(id, true);
		review.threads.reading.markRead(id);
		flushSync();

		expect(said).toHaveLength(1);
		stop();
	});
});
