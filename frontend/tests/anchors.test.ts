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
	sameSpot,
	threadPlaceOf
} from '$lib/anchors/views';
import type { StoryAnchor, StoryBlock } from '$lib/types';

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

	it('hangs on lines of its file', () => {
		expect(threadPlaceOf(range)).toEqual({ on: 'lines', lines: range });
	});
});

/** A thread's anchor on a block of the story, quoting the words it says. */
function onTheStory(block: StoryBlock, words = 'Whether it holds.'): StoryAnchor {
	return { kind: 'story', block, quote: [words], outdated: false };
}

describe('a thread on the story is named by the block it is on', () => {
	const doubt = onTheStory({ at: 'overview', text: 'doubt' });
	const secondDecision = onTheStory({ at: 'item', list: 'decisions', item: 1 });
	const turnedDown = onTheStory({ at: 'item', list: 'turned_down', item: 0 });
	const chapterWhy = onTheStory({ at: 'chapter', chapter: 'images-kept', text: 'why' });
	const chapterDoubt = onTheStory({ at: 'chapter', chapter: 'images-kept', text: 'doubt' });
	const reason = onTheStory({ at: 'reason', file: 'src/claude_review/routes.py', first_line: 42 });

	it('says the block in its own header', () => {
		expect(anchorLabel(doubt)).toBe('Doubt');
		expect(anchorLabel(secondDecision)).toBe('Decision 2');
		expect(anchorLabel(turnedDown)).toBe('Turned down 1');
		expect(anchorLabel(chapterWhy)).toBe('Why');
		expect(anchorLabel(chapterDoubt)).toBe('Where to doubt');
		expect(anchorLabel(reason)).toBe('Reason');
	});

	it('names the story, and the chapter or the step the block is of, where there is room', () => {
		expect(anchorPlace(doubt)).toBe('Story · Doubt');
		expect(anchorPlace(secondDecision)).toBe('Story · Decision 2');
		expect(anchorPlace(chapterWhy)).toBe('Story · images-kept · Why');
		expect(anchorPlace(reason)).toBe('Story · src/claude_review/routes.py:42 · Reason');
	});

	it('names only the chapter, the file or the story in a chip', () => {
		expect(anchorShortPlace(doubt)).toBe('Story · Doubt');
		expect(anchorShortPlace(chapterWhy)).toBe('images-kept · Why');
		expect(anchorShortPlace(reason)).toBe('routes.py:42 · Reason');
	});

	it('is mentioned in a panel message by the block it is on', () => {
		expect(anchorToken(doubt)).toBe('@story:doubt');
		expect(anchorToken(secondDecision)).toBe('@story:decision-2');
		expect(anchorToken(turnedDown)).toBe('@story:turned-down-1');
		expect(anchorToken(chapterWhy)).toBe('@story:images-kept:why');
		expect(anchorToken(reason)).toBe('@story:src/claude_review/routes.py:42');
	});

	it('is mentioned by its token at the end of a sentence, and not by a longer one that starts the same', () => {
		const onChapterDoubt = onTheStory({ at: 'chapter', chapter: 'doubt', text: 'why' });

		expect(anchorMentionsIn('see @story:doubt. And @story:doubt: twice', doubt)).toEqual([4, 22]);
		expect(anchorMentionsIn(anchorToken(onChapterDoubt), doubt)).toEqual([]);
		expect(anchorMentionsIn('see @story:decision-20', secondDecision)).toEqual([]);
	});

	it('is the same spot as another on the same block, whatever words they quote', () => {
		expect(sameSpot(chapterWhy, onTheStory(chapterWhy.block, 'Other words.'))).toBe(true);
		expect(sameSpot(chapterWhy, chapterDoubt)).toBe(false);
		expect(sameSpot(secondDecision, turnedDown)).toBe(false);
	});

	it('is never the same spot as a thread on lines', () => {
		expect(sameSpot(chapterWhy, lineAnchor('a.py', 'new', 1, 1, []))).toBe(false);
	});

	it('was written against the words it quotes, and no suggestion in it replaces them', () => {
		expect(anchorWrittenAgainst(doubt)).toEqual(['Whether it holds.']);
		expect(anchorReplaces(doubt)).toEqual([]);
	});

	it('hangs on the story, at its block', () => {
		expect(threadPlaceOf(reason)).toEqual({ on: 'story', block: reason.block });
	});
});
