import { describe, it, expect } from 'vitest';
import { highlightFile, languageOf } from '$lib/utils/highlight';
import type { DiffFile, DiffLine } from '$lib/types';
import { addedLine, contextLine, diffFile, hunk, removedLine } from './diff';

/** A line the change left alone, at the same number in both versions. */
function context(lineNumber: number, content: string): DiffLine {
	return contextLine(lineNumber, lineNumber, content);
}

function fileOf(lines: DiffLine[], path = 'src/thing.py'): DiffFile {
	return diffFile({ path, hunks: [hunk(lines)] });
}

describe("the colours of a file's code", () => {
	it('keeps a docstring coloured on every one of its lines', () => {
		const file = fileOf([
			context(1, 'def load():'),
			context(2, '    """Read the config.'),
			context(3, ''),
			context(4, '    Falls back to defaults.'),
			context(5, '    """'),
			context(6, '    return 1')
		]);

		const [highlighted] = highlightFile(file, 'python');

		// Lines 2-5 are one string literal; the middle ones are the regression
		expect(highlighted[1]).toContain('hljs-string');
		expect(highlighted[3]).toContain('hljs-string');
		expect(highlighted[4]).toContain('hljs-string');
	});

	it('does not colour code after a docstring as if it were still inside one', () => {
		const file = fileOf([context(1, '"""Module docs."""'), context(2, 'import os'), context(3, 'VALUE = 1')]);

		const [highlighted] = highlightFile(file, 'python');

		expect(highlighted[1]).toContain('hljs-keyword');
		expect(highlighted[2]).not.toContain('hljs-string');
	});

	it('produces one entry per row, in order', () => {
		const file = fileOf([context(1, 'a = 1'), context(2, 'b = 2')]);

		const [highlighted] = highlightFile(file, 'python');

		expect(highlighted).toHaveLength(2);
		expect(highlighted[0]).toContain('a');
		expect(highlighted[1]).toContain('b');
	});

	it('reads each side of a replacement as its own version of the file', () => {
		// The removed line opens a string the added line does not
		const file = fileOf([
			context(1, 'x = 1'),
			removedLine(2, 'note = "old'),
			addedLine(2, 'note = "new"'),
			context(3, 'y = 2')
		]);

		const [highlighted] = highlightFile(file, 'python');

		// The trailing context line belongs to both sides and is plain code
		expect(highlighted[3]).not.toContain('hljs-string');
	});

	it('escapes markup when there is no language', () => {
		const file = fileOf([context(1, '<script>alert(1)</script>')], 'notes.unknown');

		const [highlighted] = highlightFile(file, null);

		expect(highlighted[0]).not.toContain('<script>');
		expect(highlighted[0]).toContain('&lt;script&gt;');
	});

	it('escapes markup inside a highlighted language too', () => {
		const file = fileOf([context(1, 'html = "<b>&</b>"')]);

		const [highlighted] = highlightFile(file, 'python');

		expect(highlighted[0]).not.toContain('<b>');
		expect(highlighted[0]).toContain('&lt;b&gt;');
	});

	it('highlights each hunk on its own so one cannot bleed into the next', () => {
		const file = diffFile({
			path: 'src/thing.py',
			hunks: [
				hunk([context(1, 'note = "unterminated')]),
				hunk([context(40, 'import os')], { old_start: 40, new_start: 40 })
			]
		});

		const hunks = highlightFile(file, 'python');

		expect(hunks).toHaveLength(2);
		expect(hunks[1][0]).toContain('hljs-keyword');
	});
});

describe('which language a file is read as', () => {
	it("is told by the file's extension", () => {
		expect(languageOf('diff', 'src/a.py')).toBe('python');
		expect(languageOf('files', 'src/a.rs')).toBe('rust');
	});

	it('is none for an extension nobody knows', () => {
		expect(languageOf('diff', 'LICENSE')).toBeNull();
		expect(languageOf('files', 'a.unknownext')).toBeNull();
	});

	it("is markdown for a transcript's messages, whose labels have no extension", () => {
		expect(languageOf('transcript', 'user (22:41) #1')).toBe('markdown');
	});
});
