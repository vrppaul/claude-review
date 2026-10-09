import { beforeEach, describe, it, expect } from 'vitest';
import type { Draft } from '$lib/drafts/draft-shapes';
import { takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import { contextLine, diffFile, hunk } from './diff';
import { THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { pushedAt } from './pushes';
import { leavePage, openReview } from './review';

// How far the review's telling had got when the page read its facts
const FACTS_READ_AT = 5;
// How far another tab had got, whose draft this page took in
const OTHER_TAB_AT = 3;
// How far the draft a reloaded page opens from had got
const DRAFT_LEFT_AT = 2;

/** A file whose first line the change left alone. */
function untouched(path: string) {
	return diffFile({ path, hunks: [hunk([contextLine(1, 1, 'x')])] });
}

/** A review's draft as another tab kept it, having taken in pushes up to `sequence`. */
function draftTakenInTo(review: Review, sequence: number): Draft {
	const draft = review.draft;
	if (draft === null) throw new Error('A review not yet sent has a draft');
	return { ...draft, told: { [THIS_RUN]: sequence } };
}

/** Leave the page with a draft kept that took in the pushes of this run up to `sequence`. */
function reloadedFrom(sequence: number, { facts = FACTS_READ_AT, attached = false } = {}): Review {
	const before = openReview();
	before.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
	const draft = draftTakenInTo(before, sequence);
	leavePage();
	localStorage.setItem('claude-review:draft', JSON.stringify(draft));
	return openReview({ files: [untouched('a.py')], facts: { sequence: facts, answerer_attached: attached } });
}

describe('taking in pushes after another tab took them in first', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview({ files: [untouched('a.py')] });
	});

	it('still takes in what they say of the review, which its draft does not keep', () => {
		review.adopt(draftTakenInTo(review, OTHER_TAB_AT));

		takePush(review, { type: 'answerer', attached: true }, pushedAt(1));
		takePush(review, { type: 'round', number: 2 }, pushedAt(2));

		expect(review.answerer.attached).toBe(true);
		expect(review.rounds.current).toBe(2);
	});

	it('goes on from where its own socket got, not from where the other tab did', () => {
		review.adopt(draftTakenInTo(review, OTHER_TAB_AT));

		expect(review.telling.heard).toEqual({ instance: THIS_RUN, sequence: 0 });
	});

	it('keeps once an answer its draft took in from the other tab', () => {
		const id = review.threads.add(newComment({ file: 'a.py', body: 'Why?' }));
		// The other tab opens on the same draft, and its socket hands it the answer first
		const elsewhere = openReview({ files: [untouched('a.py')] });
		elsewhere.threads.receiveReply(id, 'Because.', null, pushedAt(1));

		review.adopt(draftTakenInTo(elsewhere, 1));
		takePush(review, { type: 'reply', thread_id: id, question_id: null, body: 'Because.' }, pushedAt(1));

		expect(review.threads.all[0].turns.map((turn) => turn.body)).toEqual(['Because.']);
	});

	it('raises once a thread its draft took in from the other tab', () => {
		const anchor = newComment({ file: 'a.py' }).anchor;
		const point = { type: 'point', thread_id: 'raised-1', anchor, body: 'Look', severity: 'note' } as const;
		takePush(review, point, pushedAt(1));
		const theirs = draftTakenInTo(review, 1);
		review = openReview({ files: [untouched('a.py')] });

		review.adopt(theirs);
		takePush(review, point, pushedAt(1));

		expect(review.threads.all.map((thread) => thread.id)).toEqual(['raised-1']);
		expect(review.conversation.turns).toHaveLength(1);
	});
});

describe('a page opening from a draft', () => {
	it('goes on from where its draft left off, when that is before its facts', () => {
		const review = reloadedFrom(DRAFT_LEFT_AT);

		expect(review.telling.heard).toEqual({ instance: THIS_RUN, sequence: DRAFT_LEFT_AT });
	});

	it('goes on from its facts, when a draft kept meanwhile got further', () => {
		const review = reloadedFrom(FACTS_READ_AT + 1);

		expect(review.telling.heard).toEqual({ instance: THIS_RUN, sequence: FACTS_READ_AT });
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
