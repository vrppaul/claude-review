import { describe, it, expect } from 'vitest';
import { detectLanguage, highlightFile } from '$lib/utils/highlight';
import type { DiffFile, DiffLine } from '$lib/types';

function context(no: number, content: string): DiffLine {
	return { type: 'context', old_no: no, new_no: no, content };
}

function fileOf(lines: DiffLine[], path = 'src/thing.py'): DiffFile {
	return {
		path,
		status: 'modified',
		hunks: [{ header: '@@ -1,4 +1,4 @@', old_start: 1, new_start: 1, lines }],
		is_binary: false,
		old_mode: null,
		new_mode: null
	};
}

describe('highlightFile', () => {
	it('keeps a docstring coloured on every one of its lines', () => {
		const file = fileOf([
			context(1, 'def load():'),
			context(2, '    """Read the config.'),
			context(3, ''),
			context(4, '    Falls back to defaults.'),
			context(5, '    """'),
			context(6, '    return 1')
		]);

		const [hunk] = highlightFile(file, 'python');

		// Lines 2-5 are one string literal; the middle ones are the regression
		expect(hunk[1]).toContain('hljs-string');
		expect(hunk[3]).toContain('hljs-string');
		expect(hunk[4]).toContain('hljs-string');
	});

	it('does not colour code after a docstring as if it were still inside one', () => {
		const file = fileOf([
			context(1, '"""Module docs."""'),
			context(2, 'import os'),
			context(3, 'VALUE = 1')
		]);

		const [hunk] = highlightFile(file, 'python');

		expect(hunk[1]).toContain('hljs-keyword');
		expect(hunk[2]).not.toContain('hljs-string');
	});

	it('produces one entry per row, in order', () => {
		const file = fileOf([context(1, 'a = 1'), context(2, 'b = 2')]);

		const [hunk] = highlightFile(file, 'python');

		expect(hunk).toHaveLength(2);
		expect(hunk[0]).toContain('a');
		expect(hunk[1]).toContain('b');
	});

	it('reads each side of a replacement as its own version of the file', () => {
		// The removed line opens a string the added line does not
		const file = fileOf([
			context(1, 'x = 1'),
			{ type: 'delete', old_no: 2, new_no: null, content: 'note = "old' },
			{ type: 'add', old_no: null, new_no: 2, content: 'note = "new"' },
			context(3, 'y = 2')
		]);

		const [hunk] = highlightFile(file, 'python');

		// The trailing context line belongs to both sides and is plain code
		expect(hunk[3]).not.toContain('hljs-string');
	});

	it('escapes markup when there is no language', () => {
		const file = fileOf([context(1, '<script>alert(1)</script>')], 'notes.unknown');

		const [hunk] = highlightFile(file, null);

		expect(hunk[0]).not.toContain('<script>');
		expect(hunk[0]).toContain('&lt;script&gt;');
	});

	it('escapes markup inside a highlighted language too', () => {
		const file = fileOf([context(1, 'html = "<b>&</b>"')]);

		const [hunk] = highlightFile(file, 'python');

		expect(hunk[0]).not.toContain('<b>');
		expect(hunk[0]).toContain('&lt;b&gt;');
	});

	it('highlights each hunk on its own so one cannot bleed into the next', () => {
		const file: DiffFile = {
			path: 'src/thing.py',
			status: 'modified',
			hunks: [
				{
					header: '@@ -1,1 +1,1 @@',
					old_start: 1,
					new_start: 1,
					lines: [context(1, 'note = "unterminated')]
				},
				{
					header: '@@ -40,1 +40,1 @@',
					old_start: 40,
					new_start: 40,
					lines: [context(40, 'import os')]
				}
			],
			is_binary: false,
			old_mode: null,
			new_mode: null
		};

		const hunks = highlightFile(file, 'python');

		expect(hunks).toHaveLength(2);
		expect(hunks[1][0]).toContain('hljs-keyword');
	});
});

describe('detectLanguage', () => {
	it('maps an extension to a language', () => {
		expect(detectLanguage('src/a.py')).toBe('python');
		expect(detectLanguage('src/a.rs')).toBe('rust');
	});

	it('returns null for an unknown extension', () => {
		expect(detectLanguage('LICENSE')).toBeNull();
		expect(detectLanguage('a.unknownext')).toBeNull();
	});
});
