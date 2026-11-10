/** What a test asks of an element the page drew, said one way in every test that asks it. */
import { vi } from 'vitest';

/** What an element says, its runs of space made one. */
export function said(element: HTMLElement): string {
	return element.textContent.replace(/\s+/g, ' ').trim();
}

/** The words a piece of markup shows, read as the browser reads it: its tags gone, its entities turned to what they stand for. */
export function textShownBy(markup: string): string {
	const holder = document.createElement('div');
	holder.innerHTML = markup;
	return holder.textContent;
}

/**
 * What records an element being brought into view: its own, given to it
 * here, never the one every element shares, which is called by whatever was
 * brought into view before.
 */
export function broughtIntoView(element: HTMLElement): ReturnType<typeof vi.fn> {
	const brought = vi.fn();
	element.scrollIntoView = brought;
	return brought;
}
