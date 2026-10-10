import { describe, it, expect } from 'vitest';
import type { Draft } from '$lib/drafts/draft-shapes';
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import { storageKey } from '$lib/utils/preferences';
import { contextLine, diffFile, hunk } from './diff';
import { THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { pushedAt } from './pushes';
import { leavePage, openReview } from './review';

// How far the review's telling had got when the page read its facts
const FACTS_READ_AT = 5;
// How far the draft a reloaded page opens from had got
const DRAFT_LEFT_AT = 2;
// A push that changes nothing a test reads
const NO_WORK = { type: 'progress', work: null } as const;

/** A file whose first line the change left alone. */
function untouched(path: string) {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

/** Reload over a draft holding one thread, kept as far as the `sequence`-th push. */
function reloadedFrom(sequence: number, { attached = false } = {}): Review {
	const before = openReview();
	before.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
	const draft = before.draft;
	if (draft === null) throw new Error('A review not yet sent has a draft');
	const kept: Draft = { ...draft, told: pushedAt(sequence) };
	leavePage();
	localStorage.setItem(storageKey('draft'), JSON.stringify(kept));
	return openReview({ files: [untouched('a.py')], facts: { sequence: FACTS_READ_AT, answerer_attached: attached } });
}

describe('the pushes a review takes in', () => {
	it('takes in once a push its socket handed over twice', () => {
		const review = openReview();

		takePush(review, { type: 'chat', message_id: null, body: 'Done.', files: [] }, pushedAt(1));
		takePush(review, { type: 'chat', message_id: null, body: 'Done.', files: [] }, pushedAt(1));

		expect(review.conversation.turns).toHaveLength(1);
	});

	it('keeps with its draft how far its socket has got', () => {
		const review = openReview();

		takePush(review, NO_WORK, pushedAt(1));

		expect(review.draft?.told).toEqual({ instance: THIS_RUN, sequence: 1 });
	});
});

describe('a page opening from a draft', () => {
	it('goes on from where its draft left off, when that is before its facts', () => {
		const review = reloadedFrom(DRAFT_LEFT_AT);

		expect(review.telling.heard).toEqual(pushedAt(DRAFT_LEFT_AT));
	});

	it('goes on from its facts, when they are no later than its draft', () => {
		const review = reloadedFrom(FACTS_READ_AT + 1);

		expect(review.telling.heard).toEqual(pushedAt(FACTS_READ_AT));
	});

	it('takes in for its draft what was said after it, but leaves the facts it read as they are', () => {
		const review = reloadedFrom(DRAFT_LEFT_AT, { attached: true });
		const id = review.threads.all[0].id;

		takePush(review, { type: 'answerer', attached: false }, pushedAt(DRAFT_LEFT_AT + 1));
		takePush(review, { type: 'reply', thread_id: id, question_id: null, body: 'Because.' }, pushedAt(FACTS_READ_AT));

		expect(review.answerer.attached).toBe(true);
		expect(review.threads.all[0].turns.map((turn) => turn.body)).toEqual(['Because.']);
	});
});
