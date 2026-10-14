import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { storyAnchor } from '$lib/anchors/story';
import DiffNotice from '$lib/components/DiffNotice.svelte';
import { catchUp, takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import type { ServerPush, SessionHello } from '$lib/types';
import { work } from './agent-work';
import {
	A_LATER_TAKE,
	contextLine,
	diffFile,
	diffResponse,
	FIRST_TAKE,
	hunk,
	reviewResponse,
	sinceRound
} from './diff';
import { fakeServer, SERVER_ERROR, takingStoryAskings, type FakeServer } from './fake-server';
import { THIS_RUN } from './fake-socket';
import { newComment, storyComment } from './new-comment';
import { inReview, openReview, settingsWithStoriesOn } from './review';
import { chatPush, handOverNext, pushedAt } from './pushes';
import { settled } from './settled';
import { ASKED, codeMovedOn, readTheStoryAgain, STOPPED, storyHeld, storyResponse, TAKEN } from './story';

/** A file whose first line the change left alone. */
function untouched(path: string) {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

// What the story said to doubt, which a thread on it quotes
const DOUBT_SAID = 'Whether an image is checked before it is kept.';

/** A server a retake lands from, holding no story: the page reads the story again after the retaken diff. */
function serverTellingNoStory(): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/story', storyResponse());
	return server;
}

let review: Review;

beforeEach(() => {
	review = openReview({ files: [untouched('a.py'), untouched('b.py')] });
});

describe('what the server pushes, taken in', () => {
	it('puts an answer under the thread it answers, unread', () => {
		const id = review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));

		handOverNext(review, { type: 'reply', thread_id: id, question_id: null, body: 'Because.' });

		expect(review.threads.all[0].turns.at(-1)?.body).toBe('Because.');
		expect(review.threads.unread.map((thread) => thread.id)).toEqual([id]);
	});

	it('offers the panel when an agent turns up, and stops offering rounds when it goes', () => {
		handOverNext(review, { type: 'answerer', attached: true });
		expect(review.answerer.attached).toBe(true);
		expect(review.layout.agentPanel.open).toBe(true);

		handOverNext(review, { type: 'answerer', attached: false });
		expect(review.answerer.attached).toBe(false);
	});

	it('counts an answer in the panel while the panel is shut', () => {
		review.layout.agentPanel.setOpen(false);

		handOverNext(review, chatPush('Done.'));

		expect(review.conversation.turns.at(-1)?.body).toBe('Done.');
		expect(review.layout.agentPanel.unread).toBe(1);
	});

	it('says the tree moved, the moment it does, without touching the diff', () => {
		const { getByTestId } = render(DiffNotice, inReview(review));

		handOverNext(review, { type: 'changed', moved_count: 3 });
		flushSync();

		expect(getByTestId('tree-moved').textContent).toContain('3');
		expect(review.diff.files.map((file) => file.path)).toEqual(['a.py', 'b.py']);
	});

	it('shows what the agent says it is doing, and nothing once it says its work is over', () => {
		const underWay = work({ text: 'reading the handler', files: ['a.py'] });

		handOverNext(review, { type: 'progress', work: underWay });
		expect(review.answerer.work).toEqual(underWay);

		handOverNext(review, { type: 'progress', work: null });
		expect(review.answerer.work).toBeNull();
	});

	it('reports what the agent says of itself', () => {
		const agent = { model: 'a model', context: '40% of its context', at: 1_000 };

		handOverNext(review, { type: 'status', agent });

		expect(review.answerer.status).toEqual(agent);
	});

	it('brings the file the agent shows into view, and makes it the one being read', () => {
		const section = document.createElement('section');
		const scrolled = vi.spyOn(section, 'scrollIntoView');
		review.sections.register('b.py', 'b.py', section);

		handOverNext(review, { type: 'show', file: 'b.py' });

		expect(scrolled).toHaveBeenCalledOnce();
		expect(review.sections.fileInView).toBe('b.py');
	});

	it('shows no file the diff on screen does not hold, though a section stands on the page under its name', () => {
		const section = document.createElement('section');
		section.scrollIntoView = vi.fn();
		review.sections.register('made-since.py', 'made-since.py', section);

		handOverNext(review, { type: 'show', file: 'made-since.py' });

		expect(section.scrollIntoView).not.toHaveBeenCalled();
	});

	it('takes in how the asking for a story stands, as the review tells it', () => {
		handOverNext(review, { type: 'story_asking', asking: TAKEN });

		expect(review.story.wait).toEqual({ kind: 'writing', asking: TAKEN });
	});

	it('says a story is being written once an agent attaches where the request waited for one', () => {
		review = openReview({ asking: ASKED });

		handOverNext(review, { type: 'answerer', attached: true });

		expect(review.story.wait).toEqual({ kind: 'writing', asking: ASKED });
	});

	it('reads the story the review holds when it says one was told', async () => {
		const told = storyHeld({ title: 'Told just now' });
		fakeServer().answer('GET /api/story', storyResponse({ held: told }));

		handOverNext(review, { type: 'story' });
		await settled();

		expect(review.story.held).toEqual(told);
	});

	it('takes the asking as ended once the review says a story told ended it: a round that moves that story on asks anew', async () => {
		const movedOn = storyHeld({}, { moved_on: codeMovedOn() });
		const server = fakeServer();
		server.answer('GET /api/story', storyResponse({ held: storyHeld() }));
		review = openReview({ story: movedOn, asking: TAKEN });

		handOverNext(review, { type: 'story' });
		handOverNext(review, { type: 'story_asking', asking: null });
		await settled();
		server.answer('GET /api/story', storyResponse({ held: movedOn }));
		await readTheStoryAgain(review.story);

		expect(review.story.wait).toEqual({ kind: 'unasked' });
	});

	it('holds the later of two stories told one after the other', async () => {
		const reads = fakeServer().hold('GET /api/story');

		handOverNext(review, { type: 'story' });
		handOverNext(review, { type: 'story' });
		await vi.waitFor(() => expect(reads.requests).toHaveLength(1));
		reads.answer(0, storyResponse({ held: storyHeld({ title: 'Told first' }) }));
		await vi.waitFor(() => expect(reads.requests).toHaveLength(2));
		reads.answer(1, storyResponse({ held: storyHeld({ title: 'Told second' }) }));
		await settled();

		expect(review.story.held?.story.title).toBe('Told second');
	});

	it('holds no story told of a take of the change the page has not taken in: it is held with that take’s diff', async () => {
		review = openReview({ story: storyHeld() });
		fakeServer().answer('GET /api/story', storyResponse({ held: storyHeld({}, { take: A_LATER_TAKE }) }));

		handOverNext(review, { type: 'story' });
		await settled();

		expect(review.story.held).toBeNull();
	});

	it('says in the panel when the story told could not be read, and keeps the one it had', async () => {
		const before = storyHeld({ title: 'Told before' });
		review = openReview({ story: before });
		fakeServer().refuse('GET /api/story', SERVER_ERROR, 'the review fell over');

		handOverNext(review, { type: 'story' });
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe('the story could not be read — the review fell over');
		expect(review.story.held).toEqual(before);
	});

	it('moves every thread on the words of the story where the review says it now hangs, once another story is told', async () => {
		const server = fakeServer();
		server.answer('GET /api/story', storyResponse({ held: storyHeld({ title: 'Told just now' }) }));
		const onTheDoubt = storyAnchor({ at: 'overview', text: 'doubt' }, DOUBT_SAID);
		const id = review.threads.add(storyComment(onTheDoubt.block, 'Checked at all?', DOUBT_SAID));
		// The new story says those words where the old one said what was done
		const movedTo = storyAnchor({ at: 'overview', text: 'done' }, DOUBT_SAID);
		server.answer('POST /api/anchors/follow', { anchors: [movedTo] });

		handOverNext(review, { type: 'story' });
		await settled();

		expect(server.bodiesSentTo('POST /api/anchors/follow')).toEqual([{ anchors: [onTheDoubt] }]);
		expect(review.threads.all.find((thread) => thread.id === id)?.anchor).toEqual(movedTo);
	});

	it('says in the panel when the threads on its words could not follow the story told', async () => {
		const server = fakeServer();
		server.answer('GET /api/story', storyResponse({ held: storyHeld({ title: 'Told just now' }) }));
		review.threads.add(storyComment({ at: 'overview', text: 'doubt' }, 'Checked at all?', DOUBT_SAID));
		server.refuse('POST /api/anchors/follow', SERVER_ERROR, 'the review fell over');

		handOverNext(review, { type: 'story' });
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe(
			'the threads could not follow the story told — the review fell over'
		);
	});

	it('moves on to the round the server began, never back', () => {
		handOverNext(review, { type: 'round', number: 3 });
		handOverNext(review, { type: 'round', number: 2 });

		expect(review.rounds.current).toBe(3);
	});

	it('puts a thread the agent raised on the diff, unread, and says so in the panel', () => {
		const anchor = newComment({ file: 'a.py' }).anchor;

		handOverNext(review, { type: 'point', thread_id: 'raised-1', anchor, body: 'Look', severity: 'note' });

		expect(review.threads.all[0].raised_by).toBe('author');
		expect(review.threads.unread.map((thread) => thread.id)).toEqual(['raised-1']);
		expect(review.conversation.turns.at(-1)?.threads).toEqual(['raised-1']);
	});

	it("counts the review's files after a retake, not those of a narrower base on screen", async () => {
		const server = serverTellingNoStory();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		// A narrower base shows one file of the review's three
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], base: sinceRound(1) }));
		const retake: ServerPush = { type: 'diff', file_count: 3, changes: null };

		handOverNext(review, retake);
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe('diff retaken · 3 files');
	});

	it('takes one retake in at a time, so threads never follow onto a diff older than the one shown', async () => {
		const server = serverTellingNoStory();
		const follows = server.hold('POST /api/anchors/follow');
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')] }));
		const retake: ServerPush = { type: 'diff', file_count: 1, changes: null };

		handOverNext(review, retake);
		handOverNext(review, retake);
		await settled();
		expect(follows.requests).toHaveLength(1);

		follows.answer(0, { anchors: [] });
		await vi.waitFor(() => expect(follows.requests).toHaveLength(2));
		follows.answer(1, { anchors: [] });
	});

	it('says the tree moved again when it moved while the retaken diff was on its way', async () => {
		const server = serverTellingNoStory();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], moved: 2 }));

		handOverNext(review, { type: 'changed', moved_count: 1 });
		handOverNext(review, { type: 'diff', file_count: 1, changes: null });
		await settled();

		expect(review.diff.treeMoved.count).toBe(2);
	});

	it('says the tree moved after a retake, though the reader waved away as many files before it', async () => {
		const server = serverTellingNoStory();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')] }));
		handOverNext(review, { type: 'changed', moved_count: 1 });
		review.diff.treeMoved.dismiss();

		handOverNext(review, { type: 'diff', file_count: 1, changes: null });
		await settled();
		handOverNext(review, { type: 'changed', moved_count: 1 });

		expect(review.diff.treeMoved.count).toBe(1);
	});

	it('says one file as one', async () => {
		const server = serverTellingNoStory();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')] }));

		handOverNext(review, { type: 'diff', file_count: 1, changes: null });
		await settled();

		expect(review.conversation.turns.at(-1)?.body).toBe('diff retaken · 1 file');
	});

	describe('with a story held', () => {
		// The story the review followed onto the diff taken again, and what the reader had read of it
		const FOLLOWED = storyHeld({}, { take: A_LATER_TAKE });
		const CHAPTER_READ = 'ch-1';
		let server: FakeServer;

		beforeEach(() => {
			review = openReview({ files: [untouched('a.py')], story: storyHeld() });
			review.story.progress.markRead(CHAPTER_READ);
			server = fakeServer();
			server.answer('POST /api/anchors/follow', { anchors: [] });
			server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], take: A_LATER_TAKE }));
			server.answer('GET /api/story', storyResponse({ held: FOLLOWED }));
		});

		it('reads the story the review followed onto the diff taken again, and holds it with that diff', async () => {
			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			await settled();

			expect([review.story.held, review.diff.takeOnScreen]).toEqual([FOLLOWED, A_LATER_TAKE]);
		});

		it('holds neither the diff taken again nor the story followed onto it until both are read', async () => {
			const stories = server.hold('GET /api/story');
			const before = review.story.held;

			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			await vi.waitFor(() => expect(stories.requests).toHaveLength(1));
			await settled();

			expect([review.story.held, review.diff.takeOnScreen]).toEqual([before, FIRST_TAKE]);
			stories.answer(0, storyResponse({ held: FOLLOWED }));
		});

		it('holds no story once the story followed onto the diff taken again cannot be read, and says so in the panel', async () => {
			server.refuse('GET /api/story', SERVER_ERROR, 'the review fell over');

			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			await settled();

			expect([review.story.held, review.diff.takeOnScreen]).toEqual([null, A_LATER_TAKE]);
			expect(review.conversation.turns.map((turn) => turn.body)).toContain(
				'the story could not be read — the review fell over'
			);
		});

		it('reads a story told while the diff is taken again once the diff and the story followed are held', async () => {
			const follows = server.hold('POST /api/anchors/follow');

			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			handOverNext(review, { type: 'story' });
			await settled();
			expect(server.requestsTo('GET /api/story')).toEqual([]);

			follows.answer(0, { anchors: [] });
			await settled();
			expect(server.requestsTo('GET /api/story')).toHaveLength(2);
		});

		it('keeps what was read of the story followed, and offers no new one', async () => {
			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			await settled();

			expect([review.story.progress.isRead(CHAPTER_READ), review.story.arrival]).toEqual([true, 'none']);
		});
	});

	describe('with a story held that the retake leaves moved on', () => {
		// The story the review followed onto the diff taken again, a round having moved the code on under it
		const MOVED_ON = storyHeld({}, { take: A_LATER_TAKE, moved_on: codeMovedOn() });

		/** A server a retake lands from, holding that story, and taking a story asked for. */
		function retakingUnderAStoryThatMovedOn(): FakeServer {
			const server = takingStoryAskings();
			server.answer('POST /api/anchors/follow', { anchors: [] });
			server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py')], take: A_LATER_TAKE }));
			server.answer('GET /api/story', storyResponse({ held: MOVED_ON }));
			return server;
		}

		it('asks for the story told again, once, where the reader turned stories on', async () => {
			const server = retakingUnderAStoryThatMovedOn();
			const settings = await settingsWithStoriesOn(server);
			review = openReview({ files: [untouched('a.py')], story: storyHeld(), settings });

			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			await settled();

			expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
		});

		it('asks for nothing where the reader left stories off', async () => {
			const server = retakingUnderAStoryThatMovedOn();
			review = openReview({ files: [untouched('a.py')], story: storyHeld() });

			handOverNext(review, { type: 'diff', file_count: 1, changes: null });
			await settled();

			expect(server.requestsTo('POST /api/story/request')).toEqual([]);
		});
	});
});

// Where the telling goes on after what could not be handed over
const GOES_ON_FROM = { instance: THIS_RUN, sequence: 0 };
// A review restarted on the same port: another run, numbering its pushes afresh
const NEXT_RUN = 'next-run';

/** A server the page can catch up from: the review as it now stands, its threads where they were, and no story told. */
function caughtUpFrom(): FakeServer {
	const server = fakeServer();
	server.answer('GET /api/review', reviewResponse());
	server.answer('POST /api/anchors/follow', { anchors: [] });
	server.answer('GET /api/diff', diffResponse({ files: [untouched('a.py'), untouched('b.py')] }));
	server.answer('GET /api/story', storyResponse());
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

	it('reads the story the review holds now, in case one was told among what was missed', async () => {
		const told = storyHeld({ title: 'Told while the page was away' });
		caughtUpFrom().answer('GET /api/story', storyResponse({ held: told }));

		await catchUp(review, GOES_ON_FROM);

		expect(review.story.held).toEqual(told);
	});

	it('reads how the asking for a story stands now, in case it changed among what was missed', async () => {
		review = openReview({ asking: TAKEN });
		caughtUpFrom().answer('GET /api/review', reviewResponse({ story_asking: STOPPED }));

		await catchUp(review, GOES_ON_FROM);

		expect(review.story.wait).toEqual({ kind: 'stopped' });
	});

	it('takes in no asking told before the facts it read again: they hold how it stands since', async () => {
		review = openReview({ asking: ASKED });
		caughtUpFrom().answer('GET /api/review', reviewResponse({ sequence: 2, story_asking: STOPPED }));
		await catchUp(review, GOES_ON_FROM);

		// Told while the page caught up, and handed over once it had
		takePush(review, { type: 'story_asking', asking: TAKEN }, pushedAt(1));

		expect(review.story.wait).toEqual({ kind: 'stopped' });
	});

	it('asks for a story again where stories are on and the review holds no asking: it was started again', async () => {
		const server = takingStoryAskings(caughtUpFrom());
		review = openReview({ settings: await settingsWithStoriesOn(server), asking: TAKEN });

		await catchUp(review, GOES_ON_FROM);

		expect(server.requestsTo('POST /api/story/request')).toHaveLength(1);
	});

	it('asks for no story after a gap where the reader left stories off', async () => {
		const server = takingStoryAskings(caughtUpFrom());

		await catchUp(review, GOES_ON_FROM);

		expect(server.requestsTo('POST /api/story/request')).toEqual([]);
	});

	it('says what catching up did, and apart from it that the story could not be read, when the story alone fails', async () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1, quote: ['x'] }));
		const moved = { ...review.threads.all[0].anchor, start_line: 2, end_line: 2 };
		const server = caughtUpFrom();
		server.answer('POST /api/anchors/follow', { anchors: [moved] });
		server.refuse('GET /api/story', SERVER_ERROR, 'the review fell over');

		await catchUp(review, GOES_ON_FROM);

		const said = review.conversation.turns.map((turn) => turn.body);
		expect(said.at(-2)).toBe('the story could not be read — the review fell over');
		expect(said.at(-1)).toContain('1 thread followed its lines');
	});

	it('asks for no story where catching up itself failed: one failure is said once', async () => {
		const server = caughtUpFrom();
		server.refuse('GET /api/review', SERVER_ERROR, 'the review fell over');

		await catchUp(review, GOES_ON_FROM);

		expect(server.requestsTo('GET /api/story')).toEqual([]);
	});

	it('asks for no story of a review that takes none', async () => {
		review = openReview({ facts: { takes_a_story: false } });
		const server = caughtUpFrom();

		await catchUp(review, GOES_ON_FROM);

		expect(server.requestsTo('GET /api/story')).toEqual([]);
	});

	it('follows the threads onto the diff as it stands, in case a retake was among what was missed', async () => {
		const id = review.threads.add(newComment({ file: 'a.py', startLine: 1, quote: ['x'] }));
		const moved = { ...review.threads.all[0].anchor, start_line: 2, end_line: 2 };
		caughtUpFrom().answer('POST /api/anchors/follow', { anchors: [moved] });

		await catchUp(review, GOES_ON_FROM);

		expect(review.threads.all.find((thread) => thread.id === id)?.anchor.start_line).toBe(2);
		expect(review.conversation.turns.at(-1)?.body).toContain('1 thread followed its lines');
	});

	it('takes the diff again, in case a retake was among what was missed', async () => {
		caughtUpFrom().answer('GET /api/diff', diffResponse({ files: [untouched('c.py')] }));

		await catchUp(review, GOES_ON_FROM);

		expect(review.diff.files.map((file) => file.path)).toEqual(['c.py']);
	});

	it('takes in what a restarted review says of its facts from then on', async () => {
		caughtUpFrom();

		await catchUp(review, { instance: NEXT_RUN, sequence: 0 });
		takePush(review, { type: 'round', number: 4 }, { instance: NEXT_RUN, sequence: 1 });

		expect(review.rounds.current).toBe(4);
	});

	it('says in the panel that what was said meanwhile may be missing, and leaves the ticks alone', async () => {
		caughtUpFrom();
		review.reading.setViewed('a.py', true);

		await catchUp(review, GOES_ON_FROM);

		expect(review.conversation.turns.at(-1)?.body).toMatch(/anything said meanwhile may be missing/);
		expect(review.reading.isViewed('a.py')).toBe(true);
	});

	it('does not take a retake in again that the facts it read hold already', async () => {
		const server = caughtUpFrom();
		server.answer('GET /api/review', reviewResponse({ sequence: 2 }));
		await catchUp(review, GOES_ON_FROM);

		// Told while the page caught up, and handed over once it had
		takePush(review, { type: 'diff', file_count: 2, changes: null }, pushedAt(1));
		await settled();

		expect(server.requestsTo('GET /api/diff')).toHaveLength(1);
	});

	it('says so when the review cannot be read again', async () => {
		caughtUpFrom().fail('GET /api/review', SERVER_ERROR);

		await catchUp(review, GOES_ON_FROM);

		expect(review.conversation.turns.at(-1)?.body).toMatch(/catching up failed/);
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
		review.threads.receiveReply(id, 'Because.', null);
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
