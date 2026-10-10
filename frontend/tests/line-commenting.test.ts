import { describe, it, expect } from 'vitest';
import { LineCommenting } from '$lib/components/line-commenting.svelte';
import { type DrawnLine, drawnHunks } from '$lib/utils/drawn-file';
import { contextLine, diffFile, hunk } from './diff';
import { SEND_LIMITS } from './pasted-images';
import type { Review } from '$lib/review/review.svelte';
import { openReview } from './review';

// The most lines the review takes in one comment, as the server would say it
const LONGEST_RANGE = 3;
// The lines of the file these tests drag over: 10 to 20, all unchanged
const FIRST_LINE = 10;
const LAST_LINE = 20;

const file = diffFile({
	path: 'a.py',
	hunks: [
		hunk(
			Array.from({ length: LAST_LINE - FIRST_LINE + 1 }, (_, offset) =>
				contextLine(FIRST_LINE + offset, FIRST_LINE + offset, `line ${FIRST_LINE + offset}`)
			),
			{ old_start: FIRST_LINE, new_start: FIRST_LINE }
		)
	]
});
const [drawn] = drawnHunks(file, null, true);

/** The line numbered this, as it is drawn. */
function line(number: number): DrawnLine {
	const found = drawn.lines.find((candidate) => candidate.place.number === number);
	if (!found) throw new Error(`Line ${number} is not drawn`);
	return found;
}

let review: Review;

function commenting(): LineCommenting {
	review = openReview({ files: [file], facts: { limits: { ...SEND_LIMITS, max_quoted_lines: LONGEST_RANGE } } });
	return new LineCommenting(review, {
		path: () => file.path,
		hunks: () => [drawn],
		reviewOwnsRemovedLines: () => true
	});
}

/** The comment the picking started. */
function started() {
	const [field] = review.threads.writing.onLinesOf(file.path);
	if (!field) throw new Error('No comment was started');
	return field;
}

describe('picking lines to comment on', () => {
	it('stops a drag at the most lines one comment may cover', () => {
		const lines = commenting();

		lines.press(line(10));
		lines.enter(line(20));
		lines.release();

		expect(lines.labelOf(started())).toBe('Lines 10-12');
	});

	it('stops a drag upwards the same way', () => {
		const lines = commenting();

		lines.press(line(20));
		lines.enter(line(10));
		lines.release();

		expect(lines.labelOf(started())).toBe('Lines 18-20');
	});

	it('opens the comment under the line the drag stopped at, however far past it the pointer went', () => {
		const lines = commenting();

		lines.press(line(10));
		lines.enter(line(20));
		lines.release();

		expect(lines.fieldsUnder({ side: 'new', number: 12 })).toEqual([started()]);
		expect(lines.fieldsUnder({ side: 'new', number: 20 })).toEqual([]);
	});

	it('shows the drag as far as it will go', () => {
		const lines = commenting();

		lines.press(line(10));
		lines.enter(line(20));

		expect(lines.isMarked({ side: 'new', number: 12 })).toBe(true);
		expect(lines.isMarked({ side: 'new', number: 13 })).toBe(false);
	});

	it('quotes the lines picked, as they read now', () => {
		const lines = commenting();

		lines.press(line(11));
		lines.enter(line(12));
		lines.release();

		expect(lines.quoteOf(started())).toEqual(['line 11', 'line 12']);
	});
});
