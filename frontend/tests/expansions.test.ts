import { describe, it, expect } from 'vitest';
import { drawnHunks } from '$lib/utils/drawn-file';
import {
	EXPAND_STEP,
	gapBelow,
	hiddenIn,
	hunkKey,
	readOf,
	type ContextGap,
	type RevealedLines,
	toContextLines,
	withRevealed
} from '$lib/utils/expansions';
import type { DiffHunk } from '$lib/types';
import { addedLine, contextLine, diffFile, hunk } from './diff';

// The most lines one read of a file hands back, as the server says
const LONGEST_READ = 2000;

/** A hunk of `count` unchanged lines from `newStart` on, numbered the same on both sides. */
function unchangedHunk(newStart: number, count: number): DiffHunk {
	const lines = Array.from({ length: count }, (_, offset) =>
		contextLine(newStart + offset, newStart + offset, `line ${newStart + offset}`)
	);
	return hunk(lines, { header: '', old_start: newStart, new_start: newStart });
}

/** The gap above the hunk at `index`, as the file is drawn. */
function gapAt(hunks: DiffHunk[], index: number): ContextGap {
	const drawn = drawnHunks(diffFile({ hunks }), null, false)[index];
	if (!drawn) throw new Error(`No hunk at ${index}`);
	return drawn.gap;
}

/** Lines read in beside hunks, and the file's length if a read has said it. */
function revealed(given: Partial<RevealedLines>): RevealedLines {
	return { above: new Map(), below: new Map(), length: null, ...given };
}

describe('how many lines a gap above a hunk hides', () => {
	it('counts the lines the diff left out before the first hunk', () => {
		expect(hiddenIn(gapAt([unchangedHunk(10, 3)], 0))).toBe(9);
	});

	it('counts nothing when a hunk starts at the top of the file', () => {
		expect(hiddenIn(gapAt([unchangedHunk(1, 3)], 0))).toBe(0);
	});

	it('counts the lines between two hunks', () => {
		// First hunk covers 1-3, second starts at 20
		expect(hiddenIn(gapAt([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1))).toBe(16);
	});

	it('shrinks as lines are revealed above the hunk below it, or below the hunk above it', () => {
		const first = unchangedHunk(1, 3);
		const second = unchangedHunk(20, 2);
		const shown = withRevealed(
			diffFile({ hunks: [first, second] }),
			revealed({
				above: new Map([[hunkKey(second), toContextLines(14, ['a', 'b', 'c', 'd', 'e', 'f'], 0)]]),
				below: new Map([[hunkKey(first), toContextLines(4, ['g', 'h'], 0)]])
			})
		);

		expect(hiddenIn(gapAt(shown.hunks, 1))).toBe(8);
	});

	it('closes once every hidden line is revealed', () => {
		const second = unchangedHunk(6, 2);
		const shown = { ...second, lines: [...toContextLines(4, ['a', 'b'], 0), ...second.lines] };

		expect(hiddenIn(gapAt([unchangedHunk(1, 3), shown], 1))).toBe(0);
	});

	it('names the hunk below it, by where that hunk starts', () => {
		expect(gapAt([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1).key).toBe(hunkKey(unchangedHunk(20, 2)));
	});
});

describe('which lines each way of widening a gap reads', () => {
	const between = gapAt([unchangedHunk(1, 3), unchangedHunk(100, 2)], 1);

	it('reads a step up from the hunk below, and draws them above it', () => {
		expect(readOf(between, 'up', LONGEST_READ)).toMatchObject({
			window: { start: 100 - EXPAND_STEP, end: 99 },
			landing: { hunk: hunkKey(unchangedHunk(100, 2)), side: 'above' }
		});
	});

	it('reads a step down from the hunk above, and draws them below it', () => {
		expect(readOf(between, 'down', LONGEST_READ)).toMatchObject({
			window: { start: 4, end: 3 + EXPAND_STEP },
			landing: { hunk: hunkKey(unchangedHunk(1, 3)), side: 'below' }
		});
	});

	it('reads every hidden line at once, down from the hunk above', () => {
		expect(readOf(between, 'all', LONGEST_READ)).toMatchObject({
			window: { start: 4, end: 99 },
			landing: { hunk: hunkKey(unchangedHunk(1, 3)), side: 'below' }
		});
	});

	it('reads no more at once than one read hands back, from where the lines are drawn', () => {
		expect(readOf(between, 'all', 10)?.window).toEqual({ start: 4, end: 13 });
		// Above the first hunk the lines are drawn against it, so the read ends there
		expect(readOf(gapAt([unchangedHunk(100, 2)], 0), 'all', 10)?.window).toEqual({ start: 90, end: 99 });
	});

	it('reads all of the gap above the first hunk up to it', () => {
		expect(readOf(gapAt([unchangedHunk(100, 2)], 0), 'all', LONGEST_READ)).toMatchObject({
			window: { start: 1, end: 99 },
			landing: { hunk: hunkKey(unchangedHunk(100, 2)), side: 'above' }
		});
	});

	it('has nothing to read down from above the first hunk', () => {
		expect(readOf(gapAt([unchangedHunk(100, 2)], 0), 'down', LONGEST_READ)).toBeNull();
	});

	it('never asks for a line before the first, or past the gap', () => {
		expect(readOf(gapAt([unchangedHunk(5, 2)], 0), 'up', LONGEST_READ)?.window).toEqual({ start: 1, end: 4 });
		expect(readOf(gapAt([unchangedHunk(1, 3), unchangedHunk(10, 2)], 1), 'down', LONGEST_READ)?.window).toEqual({
			start: 4,
			end: 9
		});
	});

	it('reads nothing when the gap is closed', () => {
		const closed = gapAt([unchangedHunk(1, 3)], 0);

		expect(readOf(closed, 'up', LONGEST_READ)).toBeNull();
		expect(readOf(closed, 'all', LONGEST_READ)).toBeNull();
	});
});

describe('the gap below the last hunk', () => {
	it('is not there when the hunk ends on a change: the diff would carry the lines after it', () => {
		const endingOnAChange = hunk([contextLine(1, 1, 'kept'), addedLine(2, 'added')]);

		expect(gapBelow(endingOnAChange, null)).toBeNull();
	});

	it('may go on, as far as nothing has said how long the file is', () => {
		const gap = gapBelow(unchangedHunk(10, 3), null);
		if (gap === null) throw new Error('No gap below the hunk');

		expect(hiddenIn(gap)).toBeNull();
		expect(readOf(gap, 'down', LONGEST_READ)).toMatchObject({
			window: { start: 13, end: 12 + EXPAND_STEP },
			landing: { hunk: hunkKey(unchangedHunk(10, 3)), side: 'below' }
		});
		expect(readOf(gap, 'up', LONGEST_READ)).toBeNull();
		expect(readOf(gap, 'all', LONGEST_READ)).toBeNull();
	});

	it('hides the rest of the file once its length is known, and reads all of it', () => {
		const gap = gapBelow(unchangedHunk(10, 3), 40);
		if (gap === null) throw new Error('No gap below the hunk');

		expect(hiddenIn(gap)).toBe(28);
		expect(readOf(gap, 'all', LONGEST_READ)?.window).toEqual({ start: 13, end: 40 });
	});

	it('hides nothing where the file ends with the hunk', () => {
		const gap = gapBelow(unchangedHunk(10, 3), 12);
		if (gap === null) throw new Error('No gap below the hunk');

		expect(hiddenIn(gap)).toBe(0);
		expect(readOf(gap, 'down', LONGEST_READ)).toBeNull();
	});

	it('numbers the old side as far behind as the hunk left it', () => {
		// One line added in the hunk: below it the old numbers run one behind
		const added = hunk([contextLine(9, 9, 'kept'), addedLine(10, 'added'), contextLine(10, 11, 'kept too')], {
			old_start: 9,
			new_start: 9
		});

		expect(gapBelow(added, null)?.oldOffset).toBe(-1);
	});
});

describe('revealed lines in the file shown', () => {
	const file = diffFile({ path: 'a.py', hunks: [unchangedHunk(10, 2)] });
	const key = hunkKey(unchangedHunk(10, 2));

	it('puts lines revealed above a hunk before its own, and those below after', () => {
		const shown = withRevealed(
			file,
			revealed({
				above: new Map([[key, toContextLines(8, ['line 8', 'line 9'], 0)]]),
				below: new Map([[key, toContextLines(12, ['line 12'], 0)]])
			})
		);

		expect(shown.hunks[0]?.lines.map((line) => line.new_number)).toEqual([8, 9, 10, 11, 12]);
	});

	it('leaves the file alone when nothing has been revealed', () => {
		expect(withRevealed(file, revealed({ length: 40 }))).toBe(file);
	});

	it('does not change the file it was given', () => {
		withRevealed(file, revealed({ above: new Map([[key, toContextLines(9, ['line 9'], 0)]]) }));

		expect(file.hunks[0]?.lines).toHaveLength(2);
	});
});

describe('lines read from the file', () => {
	it('numbers lines from where the window started', () => {
		const lines = toContextLines(5, ['a', 'b'], 0);

		expect(lines).toEqual([
			{ kind: 'context', old_number: 5, new_number: 5, content: 'a' },
			{ kind: 'context', old_number: 6, new_number: 6, content: 'b' }
		]);
	});

	it('numbers both gutters, like every other context line', () => {
		// The old side runs two behind by this point in the file
		const lines = toContextLines(10, ['a'], -2);

		expect(lines[0]).toEqual({ kind: 'context', old_number: 8, new_number: 10, content: 'a' });
	});
});
