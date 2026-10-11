import { describe, it, expect } from 'vitest';
import fastCheck from 'fast-check';
import { hasSuggestion, splitSuggestions, suggestedChange, withSuggestion } from '$lib/utils/suggestion';

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

describe('a suggestion whose lines hold backticks', () => {
	it('is fenced longer than any run of backticks in it, so none of them closes it', () => {
		const { text } = withSuggestion('', ['const fence = "```";', 'done();']);

		expect(text.startsWith('````suggestion\n')).toBe(true);
		expect(splitSuggestions(text)).toEqual([{ kind: 'suggestion', text: 'const fence = "```";\ndone();' }]);
	});

	it('is read back to its last line when a line in it is a fence of its own', () => {
		const { text } = withSuggestion('Keep the example:', ['```js', 'run();', '```', '````']);

		expect(splitSuggestions(text)).toEqual([
			{ kind: 'prose', text: 'Keep the example:' },
			{ kind: 'suggestion', text: '```js\nrun();\n```\n````' }
		]);
	});

	it('is read back as written by hand, with a longer fence closed by one at least as long', () => {
		const written = 'Rather:\n\n`````suggestion\nx = "````"\n```````\nand that is all';

		expect(splitSuggestions(written)).toEqual([
			{ kind: 'prose', text: 'Rather:' },
			{ kind: 'suggestion', text: 'x = "````"' },
			{ kind: 'prose', text: 'and that is all' }
		]);
		expect(hasSuggestion(written)).toBe(true);
	});

	it('is not closed by backticks in the middle of a line', () => {
		expect(splitSuggestions('```suggestion\nx = 1 ```\n```')).toEqual([{ kind: 'suggestion', text: 'x = 1 ```' }]);
	});
});

describe('a suggestion of any text', () => {
	// Characters that make or break a fence, and the line endings a reader may stop at
	const FENCE_CHARACTERS = ['`', '\n', '\r', '\u2028', ' ', 'a', 's'];
	const anyText = fastCheck.string({ unit: fastCheck.constantFrom(...FENCE_CHARACTERS), maxLength: 40 });

	it('is read back as written, whatever it holds', () => {
		fastCheck.assert(
			fastCheck.property(anyText, (suggested) => {
				const { text } = withSuggestion('A note', suggested.split('\n'));

				expect(splitSuggestions(text)).toEqual([
					{ kind: 'prose', text: 'A note' },
					{ kind: 'suggestion', text: suggested }
				]);
			})
		);
	});
});

describe('what a suggestion changes', () => {
	it('marks only the lines it changes, between the lines it keeps', () => {
		const lines = suggestedChange(['first();', 'second();', 'third();'], 'first();\nsecond(again);\nthird();');

		expect(lines).toEqual([
			{ change: 'kept', text: 'first();' },
			{ change: 'removed', text: 'second();' },
			{ change: 'added', text: 'second(again);' },
			{ change: 'kept', text: 'third();' }
		]);
	});

	it('takes everything away and puts everything there when nothing is kept', () => {
		expect(suggestedChange(['a', 'b'], 'c')).toEqual([
			{ change: 'removed', text: 'a' },
			{ change: 'removed', text: 'b' },
			{ change: 'added', text: 'c' }
		]);
	});

	it('reads back every line of both sides, each once, whatever they hold', () => {
		fastCheck.assert(
			fastCheck.property(
				fastCheck.array(fastCheck.constantFrom('a', 'b', 'c', '')),
				fastCheck.array(fastCheck.constantFrom('a', 'b', 'c', ''), { minLength: 1 }),
				(replaced, suggested) => {
					const lines = suggestedChange(replaced, suggested.join('\n'));
					const before = lines.filter((line) => line.change !== 'added').map((line) => line.text);
					const after = lines.filter((line) => line.change !== 'removed').map((line) => line.text);
					expect(before).toEqual(replaced);
					expect(after).toEqual(suggested);
				}
			)
		);
	});
});
