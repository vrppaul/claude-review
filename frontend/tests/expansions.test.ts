import { describe, it, expect } from 'vitest';
import {
	hiddenAbove,
	nextWindow,
	withRevealed,
	toContextLines,
	EXPAND_STEP
} from '$lib/utils/expansions';
import type { DiffFile, DiffHunk, DiffLine } from '$lib/types';

function hunk(newStart: number, count: number): DiffHunk {
	const lines: DiffLine[] = Array.from({ length: count }, (_, i) => ({
		type: 'context',
		old_no: newStart + i,
		new_no: newStart + i,
		content: `line ${newStart + i}`
	}));
	return { header: '', old_start: newStart, new_start: newStart, lines };
}

describe('hiddenAbove', () => {
	it('counts the lines the diff left out before the first hunk', () => {
		expect(hiddenAbove([hunk(10, 3)], 0, 0)).toBe(9);
	});

	it('counts nothing when a hunk starts at the top of the file', () => {
		expect(hiddenAbove([hunk(1, 3)], 0, 0)).toBe(0);
	});

	it('counts the lines between two hunks', () => {
		// First hunk covers 1-3, second starts at 20
		expect(hiddenAbove([hunk(1, 3), hunk(20, 2)], 1, 0)).toBe(16);
	});

	it('shrinks as lines are revealed', () => {
		expect(hiddenAbove([hunk(1, 3), hunk(20, 2)], 1, 6)).toBe(10);
	});

	it('never goes below zero', () => {
		expect(hiddenAbove([hunk(1, 3), hunk(20, 2)], 1, 99)).toBe(0);
	});
});

describe('nextWindow', () => {
	it('asks for the lines just above the hunk', () => {
		expect(nextWindow([hunk(100, 2)], 0, 0)).toEqual({
			start: 100 - EXPAND_STEP,
			end: 99
		});
	});

	it('continues from where the last reveal stopped', () => {
		expect(nextWindow([hunk(100, 2)], 0, EXPAND_STEP)).toEqual({
			start: 100 - 2 * EXPAND_STEP,
			end: 99 - EXPAND_STEP
		});
	});

	it('takes a small gap in one go rather than in pieces', () => {
		expect(nextWindow([hunk(1, 3), hunk(12, 2)], 1, 0)).toEqual({ start: 4, end: 11 });
	});

	it('never asks for a line before the first', () => {
		const window = nextWindow([hunk(5, 2)], 0, 0);

		expect(window).toEqual({ start: 1, end: 4 });
	});

	it('reports nothing left when the gap is closed', () => {
		expect(nextWindow([hunk(1, 3)], 0, 0)).toBeNull();
	});
});

describe('withRevealed', () => {
	const file: DiffFile = {
		path: 'a.py',
		status: 'modified',
		hunks: [hunk(10, 2)],
		is_binary: false,
		old_mode: null,
		new_mode: null
	};

	it('puts revealed lines inside the hunk they sit above', () => {
		const revealed = new Map([[0, toContextLines(8, ['line 8', 'line 9'])]]);

		const shown = withRevealed(file, revealed);

		expect(shown.hunks[0].lines.map((l) => l.new_no)).toEqual([8, 9, 10, 11]);
	});

	it('leaves the file alone when nothing has been revealed', () => {
		expect(withRevealed(file, new Map())).toBe(file);
	});

	it('does not change the file it was given', () => {
		withRevealed(file, new Map([[0, toContextLines(9, ['line 9'])]]));

		expect(file.hunks[0].lines).toHaveLength(2);
	});
});

describe('toContextLines', () => {
	it('numbers lines from where the window started', () => {
		const lines = toContextLines(5, ['a', 'b']);

		expect(lines).toEqual([
			{ type: 'context', old_no: null, new_no: 5, content: 'a' },
			{ type: 'context', old_no: null, new_no: 6, content: 'b' }
		]);
	});
});
