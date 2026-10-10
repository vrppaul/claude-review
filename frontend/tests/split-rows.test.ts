import { describe, it, expect } from 'vitest';
import type { DiffLine } from '$lib/types';
import { drawnHunks } from '$lib/utils/drawn-file';
import { splitRows } from '$lib/utils/split-rows';
import { addedLine, contextLine, diffFile, hunk, removedLine } from './diff';

/** The rows two columns draw these lines in, as one hunk of a file. */
function buildSplitRows(lines: DiffLine[]) {
	const [drawn] = drawnHunks(diffFile({ hunks: [hunk(lines)] }), null, true);
	return splitRows(drawn?.lines ?? []);
}

describe('the rows of the two-column layout', () => {
	it('puts an unchanged line on both sides of the same row', () => {
		const rows = buildSplitRows([contextLine(1, 1, 'import os')]);

		expect(rows).toHaveLength(1);
		expect(rows[0].left?.line.content).toBe('import os');
		expect(rows[0].right?.line.content).toBe('import os');
	});

	it('faces a removal with the addition that replaced it', () => {
		const rows = buildSplitRows([removedLine(2, 'x = 1'), addedLine(2, 'x = 2')]);

		expect(rows).toHaveLength(1);
		expect(rows[0].left?.line.content).toBe('x = 1');
		expect(rows[0].right?.line.content).toBe('x = 2');
	});

	it('leaves the right side empty when more was removed than added', () => {
		const rows = buildSplitRows([removedLine(2, 'a'), removedLine(3, 'b'), addedLine(2, 'a2')]);

		expect(rows).toHaveLength(2);
		expect(rows[1].left?.line.content).toBe('b');
		expect(rows[1].right).toBeNull();
	});

	it('leaves the left side empty when more was added than removed', () => {
		const rows = buildSplitRows([removedLine(2, 'a'), addedLine(2, 'a2'), addedLine(3, 'b2')]);

		expect(rows).toHaveLength(2);
		expect(rows[1].left).toBeNull();
		expect(rows[1].right?.line.content).toBe('b2');
	});

	it('puts a pure insertion on the right alone', () => {
		const rows = buildSplitRows([contextLine(1, 1, 'a'), addedLine(2, 'new')]);

		expect(rows[1].left).toBeNull();
		expect(rows[1].right?.line.content).toBe('new');
	});

	it('knows each row by the lines on it, so it stays the same row whatever is drawn above it', () => {
		const lines = [contextLine(5, 5, 'a'), removedLine(6, 'b'), addedLine(6, 'c')];
		const revealedAbove = [contextLine(3, 3, 'three'), contextLine(4, 4, 'four')];

		const before = buildSplitRows(lines).map((row) => row.key);
		const after = buildSplitRows([...revealedAbove, ...lines]).map((row) => row.key);

		expect(after.slice(revealedAbove.length)).toEqual(before);
		expect(new Set(after).size).toBe(after.length);
	});

	it('are none for a hunk with no lines', () => {
		expect(splitRows([])).toEqual([]);
	});
});
