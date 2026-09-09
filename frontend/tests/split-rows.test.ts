import { describe, it, expect } from 'vitest';
import { buildSplitRows } from '$lib/utils/split-rows';
import type { DiffLine } from '$lib/types';

function context(oldNo: number, newNo: number, content: string): DiffLine {
	return { type: 'context', old_no: oldNo, new_no: newNo, content };
}
function removed(oldNo: number, content: string): DiffLine {
	return { type: 'delete', old_no: oldNo, new_no: null, content };
}
function added(newNo: number, content: string): DiffLine {
	return { type: 'add', old_no: null, new_no: newNo, content };
}

describe('buildSplitRows', () => {
	it('puts an unchanged line on both sides of the same row', () => {
		const rows = buildSplitRows([context(1, 1, 'import os')]);

		expect(rows).toHaveLength(1);
		expect(rows[0].left?.line.content).toBe('import os');
		expect(rows[0].right?.line.content).toBe('import os');
	});

	it('faces a removal with the addition that replaced it', () => {
		const rows = buildSplitRows([removed(2, 'x = 1'), added(2, 'x = 2')]);

		expect(rows).toHaveLength(1);
		expect(rows[0].left?.line.content).toBe('x = 1');
		expect(rows[0].right?.line.content).toBe('x = 2');
	});

	it('leaves the right side empty when more was removed than added', () => {
		const rows = buildSplitRows([removed(2, 'a'), removed(3, 'b'), added(2, 'a2')]);

		expect(rows).toHaveLength(2);
		expect(rows[1].left?.line.content).toBe('b');
		expect(rows[1].right).toBeUndefined();
	});

	it('leaves the left side empty when more was added than removed', () => {
		const rows = buildSplitRows([removed(2, 'a'), added(2, 'a2'), added(3, 'b2')]);

		expect(rows).toHaveLength(2);
		expect(rows[1].left).toBeUndefined();
		expect(rows[1].right?.line.content).toBe('b2');
	});

	it('puts a pure insertion on the right alone', () => {
		const rows = buildSplitRows([context(1, 1, 'a'), added(2, 'new')]);

		expect(rows[1].left).toBeUndefined();
		expect(rows[1].right?.line.content).toBe('new');
	});

	it('keeps the position of each line in the hunk, so a comment can anchor to it', () => {
		const rows = buildSplitRows([context(1, 1, 'a'), removed(2, 'b'), added(2, 'c')]);

		expect(rows[0].left?.index).toBe(0);
		expect(rows[1].left?.index).toBe(1);
		expect(rows[1].right?.index).toBe(2);
	});

	it('handles a hunk with no lines', () => {
		expect(buildSplitRows([])).toEqual([]);
	});
});
