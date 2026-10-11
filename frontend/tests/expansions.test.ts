import { describe, it, expect } from 'vitest';
import { drawnHunks } from '$lib/utils/drawn-file';
import { hunkKey, withRevealed, toContextLines, EXPAND_STEP } from '$lib/utils/expansions';
import type { DiffHunk } from '$lib/types';
import { contextLine, diffFile, hunk } from './diff';

/** A hunk of `count` unchanged lines from `newStart` on, numbered the same on both sides. */
function unchangedHunk(newStart: number, count: number): DiffHunk {
	const lines = Array.from({ length: count }, (_, offset) =>
		contextLine(newStart + offset, newStart + offset, `line ${newStart + offset}`)
	);
	return hunk(lines, { header: '', old_start: newStart, new_start: newStart });
}

/** The gap above the hunk at `index`, as the file is drawn. */
function gapAt(hunks: DiffHunk[], index: number) {
	return drawnHunks(diffFile({ hunks }), null, false)[index].gap;
}

describe('how many lines a gap above a hunk hides', () => {
	it('counts the lines the diff left out before the first hunk', () => {
		expect(gapAt([unchangedHunk(10, 3)], 0).hidden).toBe(9);
	});

	it('counts nothing when a hunk starts at the top of the file', () => {
		expect(gapAt([unchangedHunk(1, 3)], 0).hidden).toBe(0);
	});

	it('counts the lines between two hunks', () => {
		// First hunk covers 1-3, second starts at 20
		expect(gapAt([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1).hidden).toBe(16);
	});

	it('shrinks as lines are revealed into the hunk below it', () => {
		const second = unchangedHunk(20, 2);
		const revealed = { ...second, lines: [...toContextLines(14, ['a', 'b', 'c', 'd', 'e', 'f'], 0), ...second.lines] };

		expect(gapAt([unchangedHunk(1, 3), revealed], 1).hidden).toBe(10);
	});

	it('closes once every hidden line is revealed', () => {
		const second = unchangedHunk(6, 2);
		const revealed = { ...second, lines: [...toContextLines(4, ['a', 'b'], 0), ...second.lines] };

		expect(gapAt([unchangedHunk(1, 3), revealed], 1).hidden).toBe(0);
	});

	it('names the hunk below it, by where that hunk starts', () => {
		expect(gapAt([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1).hunk).toBe(hunkKey(unchangedHunk(20, 2)));
	});
});

describe('which lines the next reveal asks for', () => {
	it('asks for the lines just above the hunk', () => {
		expect(gapAt([unchangedHunk(100, 2)], 0).next).toEqual({
			start: 100 - EXPAND_STEP,
			end: 99
		});
	});

	it('continues from where the last reveal stopped', () => {
		const hunk = unchangedHunk(100, 2);
		const lines = Array.from({ length: EXPAND_STEP }, (_, offset) => `line ${offset}`);
		const revealed = { ...hunk, lines: [...toContextLines(100 - EXPAND_STEP, lines, 0), ...hunk.lines] };

		expect(gapAt([revealed], 0).next).toEqual({
			start: 100 - 2 * EXPAND_STEP,
			end: 99 - EXPAND_STEP
		});
	});

	it('takes a small gap in one go rather than in pieces', () => {
		expect(gapAt([unchangedHunk(1, 3), unchangedHunk(12, 2)], 1).next).toEqual({
			start: 4,
			end: 11
		});
	});

	it('never asks for a line before the first', () => {
		expect(gapAt([unchangedHunk(5, 2)], 0).next).toEqual({ start: 1, end: 4 });
	});

	it('reports nothing left when the gap is closed', () => {
		expect(gapAt([unchangedHunk(1, 3)], 0).next).toBeNull();
	});
});

describe('revealed lines in the file shown', () => {
	const file = diffFile({ path: 'a.py', hunks: [unchangedHunk(10, 2)] });

	it('puts revealed lines inside the hunk they sit above', () => {
		const revealed = new Map([[hunkKey(file.hunks[0]), toContextLines(8, ['line 8', 'line 9'], 0)]]);

		const shown = withRevealed(file, revealed);

		expect(shown.hunks[0].lines.map((line) => line.new_number)).toEqual([8, 9, 10, 11]);
	});

	it('leaves the file alone when nothing has been revealed', () => {
		expect(withRevealed(file, new Map())).toBe(file);
	});

	it('does not change the file it was given', () => {
		withRevealed(file, new Map([[hunkKey(file.hunks[0]), toContextLines(9, ['line 9'], 0)]]));

		expect(file.hunks[0].lines).toHaveLength(2);
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
