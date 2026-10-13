import { afterEach, describe, it, expect } from 'vitest';
import { tick } from 'svelte';
import { isTypingTarget, lendKeyboardToWhatRemains } from '$lib/dom/keyboard';

/** Something drawn on the page, by its tag. */
function drawn(tag: string): HTMLElement {
	return document.body.appendChild(document.createElement(tag));
}

afterEach(() => {
	document.body.replaceChildren();
});

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

describe('words lent the keyboard, where what held it went and no control remains', () => {
	it('hold it once the page has drawn what changed', async () => {
		const heading = drawn('h2');

		lendKeyboardToWhatRemains(() => heading);
		await tick();

		expect(document.activeElement).toBe(heading);
	});

	it('are left alone while something else holds the keyboard', async () => {
		const heading = drawn('h2');
		const control = drawn('button');
		control.focus();

		lendKeyboardToWhatRemains(() => heading);
		await tick();

		expect(document.activeElement).toBe(control);
	});

	it('take it no more once it has left them: a press on them puts it on nothing, as on any words', async () => {
		const heading = drawn('h2');
		const control = drawn('button');
		lendKeyboardToWhatRemains(() => heading);
		await tick();
		control.focus();

		heading.focus();

		expect(document.activeElement).toBe(control);
	});

	it('can hold it still when it was the window that lost it, and the reader is back', async () => {
		const heading = drawn('h2');
		lendKeyboardToWhatRemains(() => heading);
		await tick();

		// A window the reader leaves blurs what holds the keyboard, which holds it still for the page
		heading.dispatchEvent(new FocusEvent('blur'));

		expect(heading.hasAttribute('tabindex')).toBe(true);
	});
});
