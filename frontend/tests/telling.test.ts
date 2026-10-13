import { describe, it, expect } from 'vitest';
import type { Draft } from '$lib/drafts/draft-shapes';
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import type { ServerPush, TellingPosition } from '$lib/types';
import { work } from './agent-work';
import { contextLine, diffFile, hunk } from './diff';
import { fakeServer } from './fake-server';
import { THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { NO_WORK, pushedAt } from './pushes';
import { leavePage, openReview } from './review';
import { settled } from './settled';
import { storeDraft } from './stored-draft';
import { storyHeld } from './story';

// How far the review's telling had got when the page read its facts
const FACTS_READ_AT = 5;
// How far the draft a reloaded page opens from had got
const DRAFT_LEFT_AT = 2;
// The run of the review before a restart, whose numbers say nothing of this one's
const EARLIER_RUN = 'earlier-run';

/** A file whose first line the change left alone. */
function untouched(path: string) {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

/** Reload over a draft holding one thread, and whatever else `written` puts in it, kept as far as `told`. */
function reloadedFrom(
	told: TellingPosition,
	{ attached = false, written = () => undefined }: { attached?: boolean; written?: (before: Review) => void } = {}
): Review {
	const before = openReview();
	before.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
	written(before);
	const draft = before.draft;
	if (draft === null) throw new Error('A review not yet sent has a draft');
	const kept: Draft = { ...draft, told };
	leavePage();
	storeDraft(kept);
	return openReview({ files: [untouched('a.py')], facts: { sequence: FACTS_READ_AT, answerer_attached: attached } });
}

describe('the pushes a review takes in', () => {
	it('keeps with its draft how far its socket has got', () => {
		const review = openReview();

		takePush(review, NO_WORK, pushedAt(1));

		expect(review.draft?.told).toEqual({ instance: THIS_RUN, sequence: 1 });
	});
});

describe('a page opening from a draft', () => {
	it('goes on from where its draft left off, when that is before its facts', () => {
		const review = reloadedFrom(pushedAt(DRAFT_LEFT_AT));

		expect(review.telling.heard).toEqual(pushedAt(DRAFT_LEFT_AT));
	});

	it('goes on from its facts, when they are no later than its draft', () => {
		const review = reloadedFrom(pushedAt(FACTS_READ_AT + 1));

		expect(review.telling.heard).toEqual(pushedAt(FACTS_READ_AT));
	});

	it('goes on from its facts when its draft was kept in another run of the review, whatever its number', () => {
		const review = reloadedFrom({ instance: EARLIER_RUN, sequence: DRAFT_LEFT_AT });

		expect(review.telling.heard).toEqual(pushedAt(FACTS_READ_AT));
	});

	it('takes in for its draft what was said after it, but leaves the facts it read as they are', () => {
		const review = reloadedFrom(pushedAt(DRAFT_LEFT_AT), { attached: true });
		const id = review.threads.all[0].id;

		takePush(review, { type: 'answerer', attached: false }, pushedAt(DRAFT_LEFT_AT + 1));
		takePush(review, { type: 'reply', thread_id: id, question_id: null, body: 'Because.' }, pushedAt(FACTS_READ_AT));

		expect(review.answerer.attached).toBe(true);
		expect(review.threads.all[0].turns.map((turn) => turn.body)).toEqual(['Because.']);
	});
});

/** A push saying something of the review's facts, and what of the review it changes when taken in. */
interface FactPush {
	push: ServerPush;
	read: (review: Review) => unknown;
}

// Each kind of push that says something of the review's facts and is taken
// in as it is heard; a retake, which takes the diff, and a story told, which
// is read from the review, are held by tests of their own
const FACT_PUSHES: FactPush[] = [
	{ push: { type: 'answerer', attached: true }, read: (review) => review.answerer.attached },
	{ push: { type: 'progress', work: work() }, read: (review) => review.answerer.work },
	{
		push: { type: 'status', agent: { model: 'another model', context: '40%', at: 1 } },
		read: (review) => review.answerer.status
	},
	{ push: { type: 'show', file: 'a.py' }, read: (review) => review.sections.fileInView },
	{ push: { type: 'changed', moved_count: 3 }, read: (review) => review.diff.treeMoved.count },
	{ push: { type: 'round', number: 9 }, read: (review) => review.rounds.current }
];

/** A page reloaded over a draft from before its facts, its one file drawn for a push to show. */
function reloadedWithAFileDrawn(): Review {
	const review = reloadedFrom(pushedAt(DRAFT_LEFT_AT));
	review.sections.register('a.py', 'a.py', document.createElement('section'));
	return review;
}

describe('a fact a page opening from a draft is told', () => {
	it.each(FACT_PUSHES)('is left as its facts say when they hold it already: $push.type', ({ push, read }) => {
		const review = reloadedWithAFileDrawn();
		const asRead = read(review);

		takePush(review, push, pushedAt(FACTS_READ_AT));

		expect(read(review)).toEqual(asRead);
	});

	it.each(FACT_PUSHES)('is taken in when it was said after them: $push.type', ({ push, read }) => {
		const review = reloadedWithAFileDrawn();
		const asRead = read(review);

		takePush(review, push, pushedAt(FACTS_READ_AT + 1));

		expect(read(review)).not.toEqual(asRead);
	});

	it('follows the threads for a retake its facts hold, and neither takes the diff again nor calls it news', async () => {
		const server = fakeServer();
		server.answerWith('POST /api/anchors/follow', (request) => request.body as { anchors: [] });
		const review = reloadedWithAFileDrawn();

		const changes = { since_round: 1, base_key: 'round:1', paths: ['a.py'] };

		takePush(review, { type: 'diff', file_count: 1, changes }, pushedAt(FACTS_READ_AT));
		await settled();

		expect(server.requestsTo('POST /api/anchors/follow')).toHaveLength(1);
		expect(server.requestsTo('GET /api/diff')).toEqual([]);
		expect(review.lastRetake.outcome).toBeNull();
		expect(review.lastRetake.changedSince).toBeNull();
	});

	it('asks for no story when one was told before its facts were read: it read that story with them', async () => {
		const server = fakeServer();
		const review = reloadedWithAFileDrawn();

		takePush(review, { type: 'story' }, pushedAt(FACTS_READ_AT));
		await settled();

		expect(server.requestsTo('GET /api/story')).toEqual([]);
	});

	it('reads the story the review holds when one was told after its facts were read', async () => {
		const toldSince = storyHeld({ title: 'Told since' });
		fakeServer().answer('GET /api/story', { held: toldSince });
		const review = reloadedWithAFileDrawn();

		takePush(review, { type: 'story' }, pushedAt(FACTS_READ_AT + 1));
		await settled();

		expect(review.story.held).toEqual(toldSince);
	});
});

describe('a page opening from a draft kept before a retake', () => {
	it('takes the tick off a file the agent rewrote meanwhile, though its facts hold the retake', async () => {
		fakeServer().answerWith('POST /api/anchors/follow', (request) => request.body as { anchors: [] });
		const review = reloadedFrom(pushedAt(DRAFT_LEFT_AT), {
			written: (before) => {
				before.reading.setViewed('rewritten.py', true);
				before.reading.setViewed('untouched.py', true);
			}
		});
		const changes = { since_round: 1, base_key: 'round:1', paths: ['rewritten.py'] };

		takePush(review, { type: 'diff', file_count: 2, changes }, pushedAt(DRAFT_LEFT_AT + 1));
		await settled();

		expect(review.reading.isViewed('rewritten.py')).toBe(false);
		expect(review.reading.isViewed('untouched.py')).toBe(true);
	});
});
