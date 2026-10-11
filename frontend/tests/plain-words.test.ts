import { describe, it, expect } from 'vitest';
import { plainWords } from '$lib/utils/plain-words';

describe('a comment in plain words, on one line', () => {
	it('keeps the words and drops the marks around them', () => {
		expect(plainWords('Rename **this**, see `parse_hunk` and [the docs](https://example.com).')).toBe(
			'Rename this, see parse_hunk and the docs.'
		);
	});

	it('reads a heading, a list and a quotation as words in a row', () => {
		expect(plainWords('# Two things\n\n- one\n- two\n\n> as you said')).toBe('Two things one two as you said');
	});

	it('says a suggested replacement as one, never its fence', () => {
		const body = 'Use the constant:\n\n```suggestion\nlimit = MAX_LINES\n```';

		expect(plainWords(body)).toBe('Use the constant: (a suggested change)');
	});

	it('keeps what was written as markup as the characters it is', () => {
		expect(plainWords('Is <b>this</b> & that safe?')).toBe('Is <b>this</b> & that safe?');
	});

	it('says nothing of a comment that says nothing', () => {
		expect(plainWords('')).toBe('');
	});
});
