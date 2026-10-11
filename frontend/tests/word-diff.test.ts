import { describe, it, expect } from 'vitest';
import fastCheck from 'fast-check';
import { escapeMarkup } from '$lib/utils/safe-markup';
import { wordRanges, markRanges, withWordMarks, type TextRange } from '$lib/utils/word-diff';
import { splitSuggestions } from '$lib/utils/suggestion';
import type { DiffLine } from '$lib/types';
import { drawnHunks } from '$lib/utils/drawn-file';
import { addedLine, contextLine, diffFile, hunk, removedLine } from './diff';

describe('the words a changed line marks', () => {
	it('marks only the part of the line that actually changed', () => {
		const { removed, added } = wordRanges('const timeout = 10;', 'const timeout = 30;');

		expect(pick('const timeout = 10;', removed)).toEqual(['10']);
		expect(pick('const timeout = 30;', added)).toEqual(['30']);
	});

	it('marks an inserted word without touching its neighbours', () => {
		const { removed, added } = wordRanges('def load(path):', 'def load(path, strict):');

		expect(pick('def load(path):', removed)).toEqual([]);
		expect(pick('def load(path, strict):', added).join('')).toBe(', strict');
	});

	it('marks a removed word', () => {
		const { removed, added } = wordRanges('from a import b, c', 'from a import b');

		expect(pick('from a import b, c', removed).join('')).toBe(', c');
		expect(added).toEqual([]);
	});

	it('gives up when most of the line is different', () => {
		// A rewritten sentence: marking nearly every word is confetti, and the
		// row colour has already said the line changed
		const { removed, added } = wordRanges(
			'tab closes. There is no persistence: closing the tab discards everything.',
			'tab closes, or when the heartbeat stops arriving for STALE_AFTER_SECONDS.'
		);

		expect(removed).toEqual([]);
		expect(added).toEqual([]);
	});

	it('joins changes separated by only a character or two', () => {
		const { added } = wordRanges('call(a, b)', 'call(x, y)');

		// "x, y" is one edit to read, not two boxes with a comma between them
		expect(added).toHaveLength(1);
		expect(pick('call(x, y)', added)).toEqual(['x, y']);
	});

	it('keeps changes at opposite ends of a line apart', () => {
		const { added } = wordRanges(
			'result = compute(first) + compute(second)',
			'result = compute(alpha) + compute(second)'
		);

		expect(added).toHaveLength(1);
	});

	it('gives up on lines with almost nothing in common', () => {
		const { removed, added } = wordRanges('return None', 'raise ValueError("boom")');

		// Marking nearly every word is noise; the row colour already says it changed
		expect(removed).toEqual([]);
		expect(added).toEqual([]);
	});

	it('reports nothing when the lines are the same', () => {
		const { removed, added } = wordRanges('x = 1', 'x = 1');

		expect(removed).toEqual([]);
		expect(added).toEqual([]);
	});
});

describe('marking words in highlighted code', () => {
	it('wraps a range of plain text', () => {
		expect(markRanges('abcdef', [{ start: 2, end: 4 }])).toBe('ab<span class="cr-word">cd</span>ef');
	});

	it('counts an escaped character as one character', () => {
		const html = 'a&amp;b';

		expect(markRanges(html, [{ start: 2, end: 3 }])).toBe('a&amp;<span class="cr-word">b</span>');
	});

	it('leaves existing markup valid when a range crosses a tag', () => {
		const html = 'a<span class="hljs-string">bc</span>d';

		const result = markRanges(html, [{ start: 0, end: 3 }]);

		expect(result).toBe(
			'<span class="cr-word">a</span><span class="hljs-string">' + '<span class="cr-word">bc</span></span>d'
		);
	});

	it('leaves the markup as it was when there is nothing to mark', () => {
		const html = '<span class="hljs-keyword">def</span> f():';

		expect(markRanges(html, [])).toBe(html);
	});
});

describe('word marks across a hunk', () => {
	/** Each line drawn as its own text, with whatever marks the hunk gives it. */
	function marked(lines: DiffLine[]): string[] {
		return withWordMarks(lines.map((line) => ({ line, markup: line.content }))).map((drawn) => drawn.markup);
	}

	it('pairs a removal with the addition that replaced it', () => {
		const lines = [removedLine(1, 'timeout = 10'), addedLine(1, 'timeout = 30')];

		const markup = marked(lines);

		expect(markup[0]).toContain('<span class="cr-word">10</span>');
		expect(markup[1]).toContain('<span class="cr-word">30</span>');
	});

	it('leaves an addition with no counterpart alone', () => {
		expect(marked([addedLine(1, 'brand new line')])).toEqual(['brand new line']);
	});

	it('pairs each removal with the addition opposite it in the run', () => {
		const lines = [removedLine(1, 'a = 1'), removedLine(2, 'b = 2'), addedLine(1, 'a = 9'), addedLine(2, 'b = 8')];

		expect(marked(lines)).toEqual([
			'a = <span class="cr-word">1</span>',
			'b = <span class="cr-word">2</span>',
			'a = <span class="cr-word">9</span>',
			'b = <span class="cr-word">8</span>'
		]);
	});

	it('leaves context lines untouched', () => {
		const lines = [contextLine(1, 1, 'unchanged'), removedLine(2, 'x = 1'), addedLine(2, 'x = 2')];

		expect(marked(lines)[0]).toBe('unchanged');
	});

	it('keeps the lines in their order, a removal past the additions starting a new replacement', () => {
		const lines = [
			addedLine(1, 'first = 1'),
			removedLine(2, 'x = 1'),
			addedLine(2, 'x = 2'),
			contextLine(3, 3, 'kept'),
			removedLine(4, 'y = 1')
		];

		const markup = marked(lines).map((text) => text.replace(/<[^>]+>/g, ''));

		expect(markup).toEqual(['first = 1', 'x = 1', 'x = 2', 'kept', 'y = 1']);
		expect(marked(lines)[1]).toContain('<span class="cr-word">1</span>');
	});

	it('are drawn in a diff, where lines are replaced, and not in files read whole', () => {
		const file = diffFile({ hunks: [hunk([removedLine(1, 'timeout = 10'), addedLine(1, 'timeout = 30')])] });

		const inDiff = drawnHunks(file, null, true)[0]?.lines.map((line) => line.markup);
		const readWhole = drawnHunks(file, null, false)[0]?.lines.map((line) => line.markup);

		expect(inDiff).toEqual(['timeout = <span class="cr-word">10</span>', 'timeout = <span class="cr-word">30</span>']);
		expect(readWhole).toEqual(['timeout = 10', 'timeout = 30']);
	});
});

function pick(text: string, ranges: TextRange[]): string[] {
	return ranges.map((range) => text.slice(range.start, range.end));
}

describe('a suggested replacement in a comment', () => {
	it('separates a suggested replacement from what was written', () => {
		const parts = splitSuggestions('Use the constant\n\n```suggestion\nx = LIMIT\n```');

		expect(parts).toEqual([
			{ kind: 'prose', text: 'Use the constant' },
			{ kind: 'suggestion', text: 'x = LIMIT' }
		]);
	});

	it('keeps a comment with no suggestion whole', () => {
		expect(splitSuggestions('Just a note')).toEqual([{ kind: 'prose', text: 'Just a note' }]);
	});

	it('keeps a multi-line suggestion together', () => {
		const parts = splitSuggestions('```suggestion\nif x:\n    return 1\n```');

		expect(parts).toEqual([{ kind: 'suggestion', text: 'if x:\n    return 1' }]);
	});
});

// What a line of code is made of here: letters, a space, and every character markup escapes
const CODE_CHARACTERS = ['a', 'b', ' ', '&', '<', '>', '"', "'"];
// The longest stretch of a line the highlighter treats as one, and the most stretches in a line
const LONGEST_STRETCH = 6;
const MOST_STRETCHES = 6;
// How the highlighter wraps a stretch it colours
const HIGHLIGHT_OPEN = '<span class="hljs-keyword">';
const SPAN_CLOSE = '</span>';
// The class the marks carry
const MARK_CLASS = 'cr-word';

/** A line as the highlighter hands it over: its text, and that text escaped with some stretches wrapped. */
const highlightedLine = fastCheck
	.array(
		fastCheck.record({
			text: fastCheck.string({
				unit: fastCheck.constantFrom(...CODE_CHARACTERS),
				minLength: 1,
				maxLength: LONGEST_STRETCH
			}),
			wrapped: fastCheck.boolean()
		}),
		{ maxLength: MOST_STRETCHES }
	)
	.map((stretches) => ({
		text: stretches.map((stretch) => stretch.text).join(''),
		html: stretches
			.map((stretch) =>
				stretch.wrapped ? `${HIGHLIGHT_OPEN}${escapeMarkup(stretch.text)}${SPAN_CLOSE}` : escapeMarkup(stretch.text)
			)
			.join('')
	}));

/** Ranges of a text of some length, in order and apart, as word ranges are. */
function rangesWithin(length: number): fastCheck.Arbitrary<TextRange[]> {
	return fastCheck
		.uniqueArray(fastCheck.integer({ min: 0, max: length }), { maxLength: length + 1 })
		.map((edges) => edges.sort((first, second) => first - second))
		.map((edges) => {
			const ranges: TextRange[] = [];
			for (let edge = 0; edge + 1 < edges.length; edge += 2) ranges.push({ start: edges[edge], end: edges[edge + 1] });
			return ranges.filter((range) => range.start < range.end);
		});
}

const lineAndRanges = highlightedLine.chain((line) =>
	rangesWithin(line.text.length).map((ranges) => ({ ...line, ranges }))
);

/** Markup as the page draws it. */
function drawn(html: string): HTMLElement {
	const holder = document.createElement('div');
	holder.innerHTML = html;
	return holder;
}

/** Which characters of the drawn text sit inside a mark, one flag per character. */
function markedCharacters(html: string): boolean[] {
	const flags: boolean[] = [];
	const walker = document.createTreeWalker(drawn(html), NodeFilter.SHOW_TEXT);
	for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
		const inMark = node.parentElement?.closest(`.${MARK_CLASS}`) !== null;
		flags.push(...Array.from(node.textContent ?? '', () => inMark));
	}
	return flags;
}

/** Whether every span opened is closed, and none is closed before it opens. */
function spansNest(html: string): boolean {
	let depth = 0;
	for (const tag of html.match(/<\/?span\b/g) ?? []) {
		depth += tag.startsWith('</') ? -1 : 1;
		if (depth < 0) return false;
	}
	return depth === 0;
}

describe('marking ranges inside highlighted markup, whatever the line', () => {
	it('changes nothing of what the line says', () => {
		fastCheck.assert(
			fastCheck.property(lineAndRanges, ({ text, html, ranges }) => {
				expect(drawn(markRanges(html, ranges)).textContent).toBe(text);
			})
		);
	});

	it('marks exactly the characters in the ranges', () => {
		fastCheck.assert(
			fastCheck.property(lineAndRanges, ({ text, html, ranges }) => {
				const wanted = [...text].map((_, index) => ranges.some((range) => index >= range.start && index < range.end));
				expect(markedCharacters(markRanges(html, ranges))).toEqual(wanted);
			})
		);
	});

	it('leaves every span closed in the order it was opened', () => {
		fastCheck.assert(
			fastCheck.property(lineAndRanges, ({ html, ranges }) => {
				expect(spansNest(markRanges(html, ranges))).toBe(true);
			})
		);
	});
});

// What a line may be made of beyond ASCII: emoji and CJK, some of them one
// UTF-16 unit, some of them two (a surrogate pair), and two emoji that share
// the first of their two units
const WIDE_CHARACTERS = ['a', ' ', '_', '(', '中', '文', '😀', '😁', '𠀀', '𠀁'];
const LONGEST_LINE = 12;
// Enough pairs of lines that two emoji sharing a unit meet in the same place
const WIDE_LINES_TRIED = 2000;
const wideLine = fastCheck.string({ unit: fastCheck.constantFrom(...WIDE_CHARACTERS), maxLength: LONGEST_LINE });

/** Whether a place in a text falls between the two units of one character. */
function splitsACharacter(text: string, place: number): boolean {
	const before = text.charCodeAt(place - 1);
	const after = text.charCodeAt(place);
	return before >= 0xd800 && before <= 0xdbff && after >= 0xdc00 && after <= 0xdfff;
}

/** Whether no range starts or ends between the two units of one character. */
function keepsCharactersWhole(text: string, ranges: TextRange[]): boolean {
	return ranges.every((range) => !splitsACharacter(text, range.start) && !splitsACharacter(text, range.end));
}

describe('the words a changed line marks, whatever script it is written in', () => {
	it('marks an emoji whole when it changes to one that shares its first unit', () => {
		const { removed, added } = wordRanges('ok 😀', 'ok 😁');

		expect(pick('ok 😀', removed)).toEqual(['😀']);
		expect(pick('ok 😁', added)).toEqual(['😁']);
	});

	it('never starts or ends a mark inside a character', () => {
		fastCheck.assert(
			fastCheck.property(wideLine, wideLine, (removedText, addedText) => {
				const { removed, added } = wordRanges(removedText, addedText);

				expect(keepsCharactersWhole(removedText, removed)).toBe(true);
				expect(keepsCharactersWhole(addedText, added)).toBe(true);
			}),
			{ numRuns: WIDE_LINES_TRIED }
		);
	});
});
