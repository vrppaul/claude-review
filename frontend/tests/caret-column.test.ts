import { describe, expect, it } from 'vitest';
import { textOffsetIn } from '$lib/dom/caret-text';
import { columnOf, wordAtCaret } from '$lib/utils/code-words';

/** A line's code as the page draws it: highlighted spans, and a mark of what changed inside one. */
function drawnCode(): HTMLElement {
	const code = document.createElement('td');
	code.innerHTML =
		'<span class="hljs-keyword">const</span> 😀 = <span class="hljs-title">re<span class="cr-word">cord</span></span>(x);';
	return code;
}

describe('the character a caret in a line of code stands at', () => {
	it('is counted across the markup the line is drawn in, in characters as the review counts them', () => {
		const code = drawnCode();
		// The caret inside the mark of what changed, before its "o": "const 😀 = rec|ord"
		const marked = code.querySelector('span span')?.firstChild as Node;

		const offset = textOffsetIn(code, { node: marked, offset: 1 });

		expect([offset, columnOf(code.textContent, offset as number)]).toEqual([14, 13]);
	});

	it('is the last letter of a word the caret stands just past, as a pointer over that letter’s right half puts it', () => {
		const text = 'const 😀 = record(x);';

		expect(wordAtCaret(text, 17)).toEqual({ start: 11, end: 17, pressed: 16 });
	});

	it('is none where the caret touches no word', () => {
		expect(wordAtCaret('a = (b);', 2)).toBeNull();
	});
});
