import { describe, it, expect } from 'vitest';
import { counted } from '$lib/utils/words';
import { fileName } from '$lib/utils/paths';

describe('a count in words', () => {
	it('says one thing in the singular', () => {
		expect(counted(1, 'file', 'files')).toBe('1 file');
	});

	it('says none, and more than one, in the plural', () => {
		expect(counted(0, 'file', 'files')).toBe('0 files');
		expect(counted(3, 'file has', 'files have')).toBe('3 files have');
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
