import { describe, it, expect } from 'vitest';
import { escapeMarkup } from '$lib/utils/safe-markup';

// Text from somebody else holding every character that could end a text node
// or a quoted attribute early, or be read as one written another way
const SAID = `it's "here" <b>bold</b> &lt;3 &amp; more`;

describe('text from somebody else written into markup', () => {
	it.each(['"', "'"])('stays one text inside an attribute quoted with %s, and inside an element', (quote) => {
		const holder = document.createElement('div');

		holder.innerHTML = `<span title=${quote}${escapeMarkup(SAID)}${quote}>${escapeMarkup(SAID)}</span>`;

		const [span, ...others] = holder.children;
		expect(others).toEqual([]);
		expect(span.getAttribute('title')).toBe(SAID);
		expect(span.textContent).toBe(SAID);
	});
});
