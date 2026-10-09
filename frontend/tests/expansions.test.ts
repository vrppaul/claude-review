import { describe, it, expect } from 'vitest';
import { hiddenAbove, nextWindow, withRevealed, toContextLines, EXPAND_STEP } from '$lib/utils/expansions';
import type { DiffHunk } from '$lib/types';
import { contextLine, diffFile, hunk } from './diff';

/** A hunk of `count` unchanged lines from `newStart` on, numbered the same on both sides. */
function unchangedHunk(newStart: number, count: number): DiffHunk {
	const lines = Array.from({ length: count }, (_, offset) =>
		contextLine(newStart + offset, newStart + offset, `line ${newStart + offset}`)
	);
	return hunk(lines, { header: '', old_start: newStart, new_start: newStart });
}

describe('how many lines a gap above a hunk hides', () => {
	it('counts the lines the diff left out before the first hunk', () => {
		expect(hiddenAbove([unchangedHunk(10, 3)], 0, 0)).toBe(9);
	});

	it('counts nothing when a hunk starts at the top of the file', () => {
		expect(hiddenAbove([unchangedHunk(1, 3)], 0, 0)).toBe(0);
	});

	it('counts the lines between two hunks', () => {
		// First hunk covers 1-3, second starts at 20
		expect(hiddenAbove([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1, 0)).toBe(16);
	});

	it('shrinks as lines are revealed', () => {
		expect(hiddenAbove([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1, 6)).toBe(10);
	});

	it('never goes below zero', () => {
		expect(hiddenAbove([unchangedHunk(1, 3), unchangedHunk(20, 2)], 1, 99)).toBe(0);
	});
});

describe('which lines the next reveal asks for', () => {
	it('asks for the lines just above the hunk', () => {
		expect(nextWindow([unchangedHunk(100, 2)], 0, 0)).toEqual({
			start: 100 - EXPAND_STEP,
			end: 99
		});
	});

	it('continues from where the last reveal stopped', () => {
		expect(nextWindow([unchangedHunk(100, 2)], 0, EXPAND_STEP)).toEqual({
			start: 100 - 2 * EXPAND_STEP,
			end: 99 - EXPAND_STEP
		});
	});

	it('takes a small gap in one go rather than in pieces', () => {
		expect(nextWindow([unchangedHunk(1, 3), unchangedHunk(12, 2)], 1, 0)).toEqual({
			start: 4,
			end: 11
		});
	});

	it('never asks for a line before the first', () => {
		const window = nextWindow([unchangedHunk(5, 2)], 0, 0);

		expect(window).toEqual({ start: 1, end: 4 });
	});

	it('reports nothing left when the gap is closed', () => {
		expect(nextWindow([unchangedHunk(1, 3)], 0, 0)).toBeNull();
	});
});

describe('revealed lines in the file shown', () => {
	const file = diffFile({ path: 'a.py', hunks: [unchangedHunk(10, 2)] });

	it('puts revealed lines inside the hunk they sit above', () => {
		const revealed = new Map([[0, toContextLines(8, ['line 8', 'line 9'], 0)]]);

		const shown = withRevealed(file, revealed);

		expect(shown.hunks[0].lines.map((line) => line.new_number)).toEqual([8, 9, 10, 11]);
	});

	it('leaves the file alone when nothing has been revealed', () => {
		expect(withRevealed(file, new Map())).toBe(file);
	});

	it('does not change the file it was given', () => {
		withRevealed(file, new Map([[0, toContextLines(9, ['line 9'], 0)]]));

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
