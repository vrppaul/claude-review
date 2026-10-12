import { describe, it, expect } from 'vitest';
import { LineCommenting } from '$lib/components/line-commenting.svelte';
import { type DrawnLine, drawnHunks } from '$lib/utils/drawn-file';
import { contextLine, diffFile, hunk, removedLine } from './diff';
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
		reviewOwnsRemovedLines: () => true,
		commentable: () => true,
		piece: () => false
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

		expect(started().at.lines).toMatchObject({ startLine: 10, endLine: 12 });
	});

	it('stops a drag upwards the same way', () => {
		const lines = commenting();

		lines.press(line(20));
		lines.enter(line(10));
		lines.release();

		expect(started().at.lines).toMatchObject({ startLine: 18, endLine: 20 });
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

	it('quotes the lines picked, as they read when picked', () => {
		const lines = commenting();

		lines.press(line(11));
		lines.enter(line(12));
		lines.release();

		expect(started().at.quote).toEqual(['line 11', 'line 12']);
	});
});

describe('picking removed lines', () => {
	/** Lines 10 and 11 removed, 12 kept, 13 removed: on the old side, 12 is not a removed line. */
	const removals = diffFile({
		path: 'b.py',
		hunks: [
			hunk(
				[
					removedLine(10, 'gone 10'),
					removedLine(11, 'gone 11'),
					contextLine(12, 10, 'kept'),
					removedLine(13, 'gone 13')
				],
				{
					old_start: 10,
					new_start: 10
				}
			)
		]
	});
	const [drawnRemovals] = drawnHunks(removals, null, true);

	function removedLines(): LineCommenting {
		review = openReview({ files: [removals], facts: { limits: { ...SEND_LIMITS, max_quoted_lines: LONGEST_RANGE } } });
		return new LineCommenting(review, {
			path: () => removals.path,
			hunks: () => [drawnRemovals],
			reviewOwnsRemovedLines: () => true,
			commentable: () => true,
			piece: () => false
		});
	}

	function removedLine13(): DrawnLine {
		const found = drawnRemovals.lines.find((candidate) => candidate.line.content === 'gone 13');
		if (!found) throw new Error('Line 13 is not drawn');
		return found;
	}

	it('stops a drag cut short on the last removed line it reaches, never on a line the change kept', () => {
		const lines = removedLines();

		lines.press(drawnRemovals.lines[0]);
		lines.enter(removedLine13());
		lines.release();

		const [field] = review.threads.writing.onLinesOf(removals.path);
		expect(field.at.lines).toMatchObject({ side: 'old', startLine: 10, endLine: 11 });
		expect(field.at.lines.opensBelow).toEqual({ side: 'old', number: 11 });
	});
});

describe('picking lines across what the diff left out', () => {
	// The most lines one comment may cover here: more than the drag below spans
	const ROOMY_RANGE = 200;
	/** Unchanged lines from `first` to `last`, numbered the same on both sides. */
	function unchanged(first: number, last: number) {
		return Array.from({ length: last - first + 1 }, (_, offset) =>
			contextLine(first + offset, first + offset, `line ${first + offset}`)
		);
	}
	// Lines 12 to 15 drawn, 16 to 35 left out by the diff, 36 to 39 drawn
	const apart = diffFile({
		path: 'c.py',
		hunks: [
			hunk(unchanged(12, 15), { old_start: 12, new_start: 12 }),
			hunk(unchanged(36, 39), { old_start: 36, new_start: 36 })
		]
	});

	function across(hunks: ReturnType<typeof drawnHunks>): LineCommenting {
		review = openReview({ files: [apart], facts: { limits: { ...SEND_LIMITS, max_quoted_lines: ROOMY_RANGE } } });
		return new LineCommenting(review, {
			path: () => apart.path,
			hunks: () => hunks,
			reviewOwnsRemovedLines: () => true,
			commentable: () => true,
			piece: () => false
		});
	}

	/** The line numbered this among drawn hunks. */
	function lineOf(hunks: ReturnType<typeof drawnHunks>, number: number): DrawnLine {
		const found = hunks.flatMap((drawnHunk) => drawnHunk.lines).find((candidate) => candidate.place.number === number);
		if (!found) throw new Error(`Line ${number} is not drawn`);
		return found;
	}

	it('stops a drag at the last line drawn before lines the diff left out', () => {
		const hunks = drawnHunks(apart, null, true);
		const lines = across(hunks);

		lines.press(lineOf(hunks, 13));
		lines.enter(lineOf(hunks, 38));
		lines.release();

		const [field] = review.threads.writing.onLinesOf(apart.path);
		expect(field.at.lines).toMatchObject({ side: 'new', startLine: 13, endLine: 15 });
		expect(field.at.quote).toEqual(['line 13', 'line 14', 'line 15']);
	});

	it('crosses into the next hunk once the lines between are drawn', () => {
		const revealed = diffFile({
			...apart,
			hunks: [
				hunk(unchanged(12, 15), { old_start: 12, new_start: 12 }),
				hunk(unchanged(16, 39), { old_start: 16, new_start: 16 })
			]
		});
		const hunks = drawnHunks(revealed, null, true);
		const lines = across(hunks);

		lines.press(lineOf(hunks, 13));
		lines.enter(lineOf(hunks, 38));
		lines.release();

		const [field] = review.threads.writing.onLinesOf(apart.path);
		expect(field.at.lines).toMatchObject({ startLine: 13, endLine: 38 });
		expect(field.at.quote).toHaveLength(26);
	});
});

describe('a file no comment may name', () => {
	it('takes no comment, by the mouse or by the keyboard', () => {
		review = openReview({ files: [file] });
		const lines = new LineCommenting(review, {
			path: () => file.path,
			hunks: () => [drawn],
			reviewOwnsRemovedLines: () => true,
			commentable: () => false,
			piece: () => false
		});

		lines.press(line(11));
		lines.enter(line(12));
		lines.release();
		lines.commentOn(line(13));

		expect(review.threads.writing.onLinesOf(file.path)).toEqual([]);
		expect(lines.isMarked({ side: 'new', number: 12 })).toBe(false);
	});
});
