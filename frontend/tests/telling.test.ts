import { describe, it, expect } from 'vitest';
import type { Draft } from '$lib/drafts/draft-shapes';
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import type { TellingPosition } from '$lib/types';
import { contextLine, diffFile, hunk } from './diff';
import { fakeServer } from './fake-server';
import { THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { NO_WORK, pushedAt } from './pushes';
import { leavePage, openReview } from './review';
import { settled } from './settled';
import { storeDraft } from './stored-draft';

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
