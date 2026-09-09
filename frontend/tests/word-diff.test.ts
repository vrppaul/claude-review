import { describe, it, expect } from 'vitest';
import { wordRanges, markRanges, applyWordMarks } from '$lib/utils/word-diff';
import type { DiffLine } from '$lib/types';

describe('wordRanges', () => {
	it('marks only the part of the line that actually changed', () => {
		const { removed, added } = wordRanges('const timeout = 10;', 'const timeout = 30;');

		expect(pick('const timeout = 10;', removed)).toEqual(['10']);
		expect(pick('const timeout = 30;', added)).toEqual(['30']);
	});

	it('marks an inserted word without touching its neighbours', () => {
		const { removed, added } = wordRanges('def load(path):', 'def load(path, strict):');

		expect(pick('def load(path):', removed)).toEqual([]);
		expect(pick('def load(path, strict):', added).join('')).toBe(', strict');
	});

	it('marks a removed word', () => {
		const { removed, added } = wordRanges('from a import b, c', 'from a import b');

		expect(pick('from a import b, c', removed).join('')).toBe(', c');
		expect(added).toEqual([]);
	});

	it('gives up when most of the line is different', () => {
		// A rewritten sentence: marking nearly every word is confetti, and the
		// row colour has already said the line changed
		const { removed, added } = wordRanges(
			'tab closes. There is no persistence: closing the tab discards everything.',
			'tab closes, or when the heartbeat stops arriving for STALE_AFTER_SECONDS.'
		);

		expect(removed).toEqual([]);
		expect(added).toEqual([]);
	});

	it('joins changes separated by only a character or two', () => {
		const { added } = wordRanges('call(a, b)', 'call(x, y)');

		// "x, y" is one edit to read, not two boxes with a comma between them
		expect(added).toHaveLength(1);
		expect(pick('call(x, y)', added)).toEqual(['x, y']);
	});

	it('keeps changes at opposite ends of a line apart', () => {
		const { added } = wordRanges(
			'result = compute(first) + compute(second)',
			'result = compute(alpha) + compute(second)'
		);

		expect(added).toHaveLength(1);
	});

	it('gives up on lines with almost nothing in common', () => {
		const { removed, added } = wordRanges('return None', 'raise ValueError("boom")');

		// Marking nearly every word is noise; the row colour already says it changed
		expect(removed).toEqual([]);
		expect(added).toEqual([]);
	});

	it('reports nothing when the lines are the same', () => {
		const { removed, added } = wordRanges('x = 1', 'x = 1');

		expect(removed).toEqual([]);
		expect(added).toEqual([]);
	});
});

describe('markRanges', () => {
	it('wraps a range of plain text', () => {
		expect(markRanges('abcdef', [[2, 4]])).toBe('ab<span class="cr-word">cd</span>ef');
	});

	it('counts an escaped character as one character', () => {
		const html = 'a&amp;b';

		expect(markRanges(html, [[2, 3]])).toBe('a&amp;<span class="cr-word">b</span>');
	});

	it('leaves existing markup valid when a range crosses a tag', () => {
		const html = 'a<span class="hljs-string">bc</span>d';

		const result = markRanges(html, [[0, 3]]);

		expect(result).toBe(
			'<span class="cr-word">a</span><span class="hljs-string">' +
				'<span class="cr-word">bc</span></span>d'
		);
	});

	it('returns the markup untouched when there is nothing to mark', () => {
		const html = '<span class="hljs-keyword">def</span> f():';

		expect(markRanges(html, [])).toBe(html);
	});
});

describe('applyWordMarks', () => {
	function line(type: DiffLine['type'], content: string): DiffLine {
		return { type, old_no: null, new_no: null, content };
	}

	it('pairs a removal with the addition that replaced it', () => {
		const lines = [line('delete', 'timeout = 10'), line('add', 'timeout = 30')];
		const html = ['timeout = 10', 'timeout = 30'];

		const marked = applyWordMarks(lines, html);

		expect(marked[0]).toContain('<span class="cr-word">10</span>');
		expect(marked[1]).toContain('<span class="cr-word">30</span>');
	});

	it('leaves an addition with no counterpart alone', () => {
		const lines = [line('add', 'brand new line')];
		const html = ['brand new line'];

		expect(applyWordMarks(lines, html)).toEqual(['brand new line']);
	});

	it('pairs each removal with the addition opposite it in the run', () => {
		const lines = [
			line('delete', 'a = 1'),
			line('delete', 'b = 2'),
			line('add', 'a = 9'),
			line('add', 'b = 8')
		];
		const html = ['a = 1', 'b = 2', 'a = 9', 'b = 8'];

		const marked = applyWordMarks(lines, html);

		expect(marked[0]).toContain('>1<');
		expect(marked[3]).toContain('>8<');
	});

	it('leaves context lines untouched', () => {
		const lines = [line('context', 'unchanged'), line('delete', 'x = 1'), line('add', 'x = 2')];
		const html = ['unchanged', 'x = 1', 'x = 2'];

		expect(applyWordMarks(lines, html)[0]).toBe('unchanged');
	});
});

function pick(text: string, ranges: [number, number][]): string[] {
	return ranges.map(([start, end]) => text.slice(start, end));
}
