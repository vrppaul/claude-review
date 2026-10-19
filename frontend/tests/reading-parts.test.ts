import { beforeEach, describe, expect, it } from 'vitest';
import { Jumps } from '$lib/dom/jump';
import { ReadingParts } from '$lib/dom/reading-parts';
import { scriptTheScroll, scrollTo } from './scripted-scroll';

// What a part of a story is known by here
const A_PART = 'a part of the story';

let parts: ReadingParts;

/** Something drawn on the page: the area a story scrolls in, a part of it, or the part's head. */
function drawn(): HTMLElement {
	return document.body.appendChild(document.createElement('div'));
}

beforeEach(() => {
	document.body.replaceChildren();
	scriptTheScroll();
	parts = new ReadingParts(new Jumps());
});

// Which part is read as a story is drawn and scrolled is held in tests/components/story-parts.test.ts
// and chapter-bar.test.ts: here, what a page can only do by taking the story off the screen
describe('an area a story is no longer read in', () => {
	it('says no part is being read, though one stood at its top', () => {
		const whole = drawn();
		parts.register(A_PART, whole, drawn());
		const stop = parts.watchInView(drawn());
		scrollTo(whole);

		stop();

		expect(parts.beingRead).toBeNull();
	});
});
