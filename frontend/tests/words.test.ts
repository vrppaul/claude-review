import { describe, it, expect } from 'vitest';
import { counted, wordsFor } from '$lib/utils/words';
import { fileName } from '$lib/utils/paths';

describe('a count in words', () => {
	const FILES = { one: 'file', many: 'files' };

	it('says one thing in the singular', () => {
		expect(counted(1, FILES)).toBe('1 file');
	});

	it('says none, and more than one, in the plural', () => {
		expect(counted(0, FILES)).toBe('0 files');
		expect(counted(3, { one: 'file has', many: 'files have' })).toBe('3 files have');
	});
});

describe('the words that go with a count, said without it', () => {
	const CHAPTERS = { one: 'chapter', many: 'chapters' };

	it('are the singular for one', () => {
		expect(wordsFor(1, CHAPTERS)).toBe('chapter');
	});

	it('are the plural for none, and for more than one', () => {
		expect(wordsFor(0, CHAPTERS)).toBe('chapters');
		expect(wordsFor(2, CHAPTERS)).toBe('chapters');
	});
});

describe('the name of a file', () => {
	it('is the last part of its path', () => {
		expect(fileName('src/lib/components/Icon.svelte')).toBe('Icon.svelte');
	});

	it('is the whole path of a file at the top', () => {
		expect(fileName('README.md')).toBe('README.md');
	});
});
