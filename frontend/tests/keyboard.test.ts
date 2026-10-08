import { describe, it, expect } from 'vitest';
import { isTypingTarget } from '$lib/utils/keyboard';

describe('which keys belong to the review', () => {
	it('leaves letters alone while a comment is being typed', () => {
		const textarea = document.createElement('textarea');

		expect(isTypingTarget(textarea)).toBe(true);
	});

	it('keeps working after a checkbox has been clicked', () => {
		// Focus parks on the hidden input behind "Viewed"; that is not typing
		const checkbox = document.createElement('input');
		checkbox.type = 'checkbox';

		expect(isTypingTarget(checkbox)).toBe(false);
	});

	it('leaves the filter box to itself', () => {
		const search = document.createElement('input');
		search.type = 'search';

		expect(isTypingTarget(search)).toBe(true);
	});
});
