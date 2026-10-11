import { describe, it, expect } from 'vitest';
import { lineAnchor } from '$lib/anchors/line';
import {
	anchorLabel,
	anchorMentionsIn,
	anchorPlace,
	anchorReplaces,
	anchorShortPlace,
	anchorToken,
	anchorWrittenAgainst,
	sameSpot
} from '$lib/anchors/views';

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

	it('is mentioned by its token, and not by a longer one that starts the same', () => {
		const short = lineAnchor('a.py', 'new', 1, 2, []);

		expect(anchorMentionsIn('see @a.py:1-2 and @a.py:1-2', short)).toEqual([4, 18]);
		expect(anchorMentionsIn('see @a.py:1-20 please', short)).toEqual([]);
	});

	it('is the same spot as another on the same lines, whatever they quote', () => {
		const quoted = lineAnchor('src/claude_review/routes.py', 'new', 42, 47, ['x']);

		expect(sameSpot(range, quoted)).toBe(true);
		expect(sameSpot(range, removed)).toBe(false);
	});

	it('was written against the lines it quotes, and a suggestion in it replaces them', () => {
		const quoted = lineAnchor('a.py', 'new', 3, 4, ['x = 1', 'y = 2']);

		expect(anchorWrittenAgainst(quoted)).toEqual(['x = 1', 'y = 2']);
		expect(anchorReplaces(quoted)).toEqual(['x = 1', 'y = 2']);
	});
});
