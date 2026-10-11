import { describe, it, expect } from 'vitest';
import { hasSuggestion, splitSuggestions, withSuggestion } from '$lib/utils/suggestion';

describe('a suggestion put into a comment', () => {
	it('stands where its lines are, so the field can select them to be edited', () => {
		const { text, start, end } = withSuggestion('Name it after the unit', ['x = 1', 'y = 2']);

		expect(text.slice(start, end)).toBe('x = 1\ny = 2');
	});

	it('is read back as the lines that were suggested, after what was written', () => {
		const { text } = withSuggestion('Name it after the unit', ['x = 1', 'y = 2']);

		expect(splitSuggestions(text)).toEqual([
			{ kind: 'prose', text: 'Name it after the unit' },
			{ kind: 'suggestion', text: 'x = 1\ny = 2' }
		]);
		expect(hasSuggestion(text)).toBe(true);
	});

	it('is all there is when nothing was written before it', () => {
		const { text, start } = withSuggestion('   ', ['x = 1']);

		expect(text.startsWith('```suggestion')).toBe(true);
		expect(text.slice(start)).toBe('x = 1\n```');
	});
});
