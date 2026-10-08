import { describe, it, expect } from 'vitest';
import { buildSplitRows } from '$lib/utils/split-rows';
import { addedLine, contextLine, removedLine } from './diff';

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
		expect(rows[1].right).toBeUndefined();
	});

	it('leaves the left side empty when more was added than removed', () => {
		const rows = buildSplitRows([removedLine(2, 'a'), addedLine(2, 'a2'), addedLine(3, 'b2')]);

		expect(rows).toHaveLength(2);
		expect(rows[1].left).toBeUndefined();
		expect(rows[1].right?.line.content).toBe('b2');
	});

	it('puts a pure insertion on the right alone', () => {
		const rows = buildSplitRows([contextLine(1, 1, 'a'), addedLine(2, 'new')]);

		expect(rows[1].left).toBeUndefined();
		expect(rows[1].right?.line.content).toBe('new');
	});

	it('keeps the position of each line in the hunk, so a comment can anchor to it', () => {
		const rows = buildSplitRows([contextLine(1, 1, 'a'), removedLine(2, 'b'), addedLine(2, 'c')]);

		expect(rows[0].left?.index).toBe(0);
		expect(rows[1].left?.index).toBe(1);
		expect(rows[1].right?.index).toBe(2);
	});

	it('are none for a hunk with no lines', () => {
		expect(buildSplitRows([])).toEqual([]);
	});
});
