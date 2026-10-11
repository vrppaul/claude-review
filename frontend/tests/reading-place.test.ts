import { describe, it, expect } from 'vitest';
import { bringBack, readingPlaceIn } from '$lib/dom/reading-place';
import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';

// jsdom lays nothing out: where each element stands is said here, in pixels
// from the top of the window, as a browser would measure it. The reader kept
// on their line across a real retake is held by tests/e2e/test_reading_place.py
const AREA_TOP = 100;
const ROW_HEIGHT = 20;

/** An element standing `top` pixels down the window, one row tall. */
function standingAt<Element extends HTMLElement>(element: Element, top: () => number): Element {
	element.getBoundingClientRect = () => DOMRect.fromRect({ y: top(), height: ROW_HEIGHT });
	return element;
}

/** A file's section whose line numbers stand one row apart from `firstTop` down, known by their places. */
function sectionOf(places: string[], firstTop: () => number): HTMLElement {
	const section = standingAt(document.createElement('section'), firstTop);
	places.forEach((place, row) => {
		const number = standingAt(document.createElement('button'), () => firstTop() + row * ROW_HEIGHT);
		number.dataset.role = LINE_NUMBER_ROLE;
		number.dataset.place = place;
		section.append(number);
	});
	return section;
}

/** The reading area, standing at its top whatever it has been scrolled by. */
function area(): HTMLElement {
	return standingAt(document.createElement('div'), () => AREA_TOP);
}

describe('where the reader is reading', () => {
	it('is the first line of the file still showing at the top of the area', () => {
		// Rows start 30 px above the area: the first is past its top, the second reaches into it
		const section = sectionOf(['new:40', 'new:41', 'new:42'], () => AREA_TOP - 30);

		expect(readingPlaceIn('b.py', section, area())).toEqual({ path: 'b.py', line: 'new:41', offset: -10 });
	});

	it('is the top of the file where it draws no line', () => {
		const section = sectionOf([], () => AREA_TOP + 5);

		expect(readingPlaceIn('b.py', section, area())).toEqual({ path: 'b.py', line: null, offset: 5 });
	});
});

describe('bringing the reader back after a new diff', () => {
	it('scrolls the line read back to where it stood, wherever the lines above it went', () => {
		const reading = area();
		// The new diff put 400 px more above the file
		const section = sectionOf(['new:40', 'new:41'], () => AREA_TOP + 400 - reading.scrollTop);

		bringBack({ path: 'b.py', line: 'new:41', offset: -10 }, section, reading);

		expect(reading.scrollTop).toBe(400 + ROW_HEIGHT + 10);
	});

	it('brings the file to the top where the line read is drawn no more', () => {
		const reading = area();
		const section = sectionOf(['new:40'], () => AREA_TOP + 400 - reading.scrollTop);

		bringBack({ path: 'b.py', line: 'new:99', offset: 50 }, section, reading);

		expect(reading.scrollTop).toBe(400);
	});
});
