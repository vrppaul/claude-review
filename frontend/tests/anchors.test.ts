import { describe, it, expect } from 'vitest';
import { lineAnchor } from '$lib/anchors/line';
import { anchorLabel, anchorPlace, anchorShortPlace, anchorSide, anchorToken } from '$lib/anchors/views';

describe('a thread on lines is named the same way wherever it is shown', () => {
	const range = lineAnchor('src/claude_review/routes.py', 'new', 42, 47, []);
	const removed = lineAnchor('src/claude_review/routes.py', 'old', 9, 9, []);

	it('says its lines in its own header', () => {
		expect(anchorLabel(range)).toBe('Lines 42-47');
		expect(anchorLabel(removed)).toBe('Removed line 9');
	});

	it('names the whole path where there is room, and only the file in a chip', () => {
		expect(anchorPlace(range)).toBe('src/claude_review/routes.py · Lines 42-47');
		expect(anchorShortPlace(range)).toBe('routes.py Lines 42-47');
	});

	it('is mentioned in a panel message by its file and lines', () => {
		expect(anchorToken(range)).toBe('@src/claude_review/routes.py:42-47');
	});

	it('says which side of the diff it hangs on', () => {
		expect(anchorSide(removed)).toBe('old');
	});
});
