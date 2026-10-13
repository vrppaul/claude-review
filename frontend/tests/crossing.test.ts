import { beforeEach, describe, expect, it } from 'vitest';
import { Crossing } from '$lib/dom/crossing';
import { areasWatching, scriptTheScroll, scrollTo } from './scripted-scroll';

// The whole of an area, as a strip of it
const THE_WHOLE_AREA = '0px';

let crossing: Crossing;

/** Something drawn on the page: an area that scrolls, or what is watched in one. */
function drawn(): HTMLElement {
	return document.body.appendChild(document.createElement('div'));
}

beforeEach(() => {
	document.body.replaceChildren();
	scriptTheScroll();
	crossing = new Crossing(THE_WHOLE_AREA);
});

describe('what crosses a strip of a scrolling area', () => {
	it('is what the reader has scrolled into it', () => {
		const shown = drawn();
		crossing.watch(drawn(), [shown]);

		scrollTo(shown);

		expect(crossing.has(shown)).toBe(true);
	});

	it('is not what was taken off the page before the browser said where it stood', () => {
		const gone = drawn();
		crossing.watch(drawn(), [gone]);
		gone.remove();

		scrollTo(gone);

		expect(crossing.has(gone)).toBe(false);
	});

	it('is nothing once the area is watched no longer', () => {
		const shown = drawn();
		const stop = crossing.watch(drawn(), [shown]);
		scrollTo(shown);

		stop();

		expect(crossing.has(shown)).toBe(false);
	});

	it('is still what crosses the strip of an area watched in its place, when the first is let go of after that', () => {
		const shown = drawn();
		const stopTheFirst = crossing.watch(drawn(), [shown]);
		crossing.watch(drawn(), [shown]);
		scrollTo(shown);

		stopTheFirst();

		expect(crossing.has(shown)).toBe(true);
	});
});

describe('an area watched no longer', () => {
	it('is watched for nothing that was drawn in it', () => {
		const drawnBefore = drawn();
		const stop = crossing.watch(drawn(), [drawnBefore]);

		stop();

		expect(areasWatching(drawnBefore)).toEqual([]);
	});

	it('is watched for nothing drawn after', () => {
		const stop = crossing.watch(drawn(), []);
		stop();
		const drawnAfter = drawn();

		crossing.add(drawnAfter);

		expect(areasWatching(drawnAfter)).toEqual([]);
	});
});
