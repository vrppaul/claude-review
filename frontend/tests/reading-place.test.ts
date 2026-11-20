import { describe, it, expect } from 'vitest';
import { bringBack, readingPlaceIn } from '$lib/dom/reading-place';
import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';
import { KEPT_IN_SIGHT_ROLE } from '$lib/dom/in-sight';
import { namesTheFileAsItStands } from '$lib/utils/line-places';

// jsdom lays nothing out: where each element stands is said here, in pixels
// from the top of the window, as a browser would measure it. The reader kept
// on their line across a real retake is held by tests/e2e/test_reading_place.py
const AREA_TOP = 100;
const AREA_HEIGHT = 400;
const ROW_HEIGHT = 20;
// A file's header kept in sight at the top of the area, over the rows that scroll under it
const HEADER_HEIGHT = 40;

/** An element standing `top` pixels down the window, one row tall unless it is taller. */
function standingAt<Element extends HTMLElement>(element: Element, top: () => number, height = ROW_HEIGHT): Element {
	element.getBoundingClientRect = () => DOMRect.fromRect({ y: top(), height });
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
	return standingAt(document.createElement('div'), () => AREA_TOP, AREA_HEIGHT);
}

/** The reading area with a file's header kept in sight at its top, and the section scrolling under it. */
function areaUnderAHeader(section: HTMLElement): HTMLElement {
	const reading = area();
	const header = standingAt(document.createElement('header'), () => AREA_TOP, HEADER_HEIGHT);
	header.dataset.role = KEPT_IN_SIGHT_ROLE;
	reading.append(header, section);
	return reading;
}

describe('where the reader is reading', () => {
	it('is the first line of the file the reader sees whole, past the header kept in sight over the rows', () => {
		// Rows start 10 px into the area: the first two lie under the header, the third is seen
		const section = sectionOf(['new:40', 'new:41', 'new:42'], () => AREA_TOP + 10);

		expect(readingPlaceIn('b.py', section, areaUnderAHeader(section), namesTheFileAsItStands)).toEqual({
			within: 'b.py',
			line: 'new:42',
			offset: 50
		});
	});

	it('is a line of the file as it stands where one is seen, though a removed line is seen above it', () => {
		const section = sectionOf(['old:7', 'new:8'], () => AREA_TOP + 20);

		expect(readingPlaceIn('b.py', section, area(), namesTheFileAsItStands)).toEqual({
			within: 'b.py',
			line: 'new:8',
			offset: 40
		});
	});

	it('is the first line seen where none of the file as it stands is', () => {
		const section = sectionOf(['old:7', 'old:8'], () => AREA_TOP + 20);

		expect(readingPlaceIn('b.py', section, area(), namesTheFileAsItStands)).toEqual({
			within: 'b.py',
			line: 'old:7',
			offset: 20
		});
	});

	it('is the top of the file where it draws no line', () => {
		const section = sectionOf([], () => AREA_TOP + 5);

		expect(readingPlaceIn('b.py', section, area(), namesTheFileAsItStands)).toEqual({
			within: 'b.py',
			line: null,
			offset: 5
		});
	});
});

describe('bringing the reader back after a new diff', () => {
	it('scrolls the line read back to where it stood, wherever the lines above it went', () => {
		const reading = area();
		// The new diff put 400 px more above the file
		const section = sectionOf(['new:40', 'new:41'], () => AREA_TOP + 400 - reading.scrollTop);

		bringBack({ within: 'b.py', line: 'new:41', offset: -10 }, section, reading);

		expect(reading.scrollTop).toBe(400 + ROW_HEIGHT + 10);
	});

	it('brings the file to the top where the line read is drawn no more', () => {
		const reading = area();
		const section = sectionOf(['new:40'], () => AREA_TOP + 400 - reading.scrollTop);

		bringBack({ within: 'b.py', line: 'new:99', offset: 50 }, section, reading);

		expect(reading.scrollTop).toBe(400);
	});
});
