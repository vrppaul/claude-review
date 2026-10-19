import { describe, it, expect } from 'vitest';
import { fitted, type LaidOut, type ScreenBox } from '$lib/ui/pane';

// A phone's window, all of it seen, and the room a pane keeps from the edges of what it is seen in
const PHONE: ScreenBox = { left: 0, top: 0, right: 420, bottom: 800 };
const ROOM = 8;
// A pane of rows, as wide as the library draws one, and how tall a pane laid out under the header stands
const MEDIUM = 320;
const TALL = 650;
// A question, as tall as its words and its two answers
const QUESTION = 90;
// Where the header's controls stand across: one at the far left, one in the middle
const FAR_LEFT = 20;
const MIDDLE = 150;
// A control's height, and how far a pane stands off it: the room its arrow takes
const CONTROL = 24;
const ARROWS_ROOM = 7;
// A control of the header, which ends this far down
const UNDER_THE_HEADER = 48;
const IN_THE_HEADER = controlAt(MIDDLE, UNDER_THE_HEADER - CONTROL);
// The reading area of a short laptop's window, beside the column of files, under the page's header and the file's
// header kept in sight over its top; and a control of it just under that header, and one near its foot
const READING_AREA: ScreenBox = { left: 240, top: 91, right: 986, bottom: 560 };
const UNDER_THE_FILES_HEADER = controlAt(READING_AREA.left + MIDDLE, 100);
const NEAR_THE_FOOT = controlAt(READING_AREA.left + MIDDLE, 480);

/** A control, by where its top left corner stands. */
function controlAt(left: number, top: number): ScreenBox {
	return { left, right: left + CONTROL, top, bottom: top + CONTROL };
}

/** A pane laid out below a control, its left edge at a place, at a width and a height, standing whole. */
function below(control: ScreenBox, left: number, width: number, height: number): LaidOut {
	const top = control.bottom + ARROWS_ROOM;
	return { standsBy: control, pane: { left, right: left + width, top, bottom: top + height }, wholeHeight: height };
}

/** A pane laid out above a control, its left edge at a place, at a width and a height, standing whole. */
function above(control: ScreenBox, left: number, width: number, height: number): LaidOut {
	const bottom = control.top - ARROWS_ROOM;
	return { standsBy: control, pane: { left, right: left + width, top: bottom - height, bottom }, wholeHeight: height };
}

describe('a pane fitted into what it is seen in', () => {
	it('stays where it lines up while it stands whole inside the window', () => {
		expect(fitted(below(IN_THE_HEADER, ROOM, MEDIUM, TALL), 'below-start', PHONE).shift).toBe(0);
	});

	it('lined up with the end of a control near the left edge, moves right to the room kept from that edge', () => {
		const laid = below(IN_THE_HEADER, FAR_LEFT - MEDIUM, MEDIUM, TALL);

		expect(laid.pane.left + fitted(laid, 'below-end', PHONE).shift).toBe(ROOM);
	});

	it('lined up with the start of a control in the middle, moves left until its right edge keeps the room', () => {
		const laid = below(IN_THE_HEADER, MIDDLE, MEDIUM, TALL);

		expect(laid.pane.right + fitted(laid, 'below-start', PHONE).shift).toBe(PHONE.right - ROOM);
	});

	it('is no wider than the window less the room either side, and keeps the end it lines up with as it narrows', () => {
		const wider = PHONE.right;
		const laid = below(IN_THE_HEADER, 0, wider, TALL);
		const fit = fitted(laid, 'below-end', PHONE);

		expect([fit.mostWidth, laid.pane.right - fit.mostWidth + fit.shift]).toEqual([PHONE.right - 2 * ROOM, ROOM]);
	});

	it('opening below, reaches down no further than the room above the window foot', () => {
		const laid = below(IN_THE_HEADER, ROOM, MEDIUM, TALL);

		expect(fitted(laid, 'below-start', PHONE).mostHeight).toBe(PHONE.bottom - ROOM - laid.pane.top);
	});

	it('opening above, reaches up no further than the room below the window top', () => {
		const laid = above(NEAR_THE_FOOT, ROOM, MEDIUM, QUESTION);

		expect(fitted(laid, 'above-start', PHONE).mostHeight).toBe(laid.pane.bottom - ROOM);
	});

	it('in a reading area beside a column, moves along to keep the room from the area’s edge, not the window’s', () => {
		const laid = below(UNDER_THE_FILES_HEADER, MIDDLE, MEDIUM, QUESTION);

		expect(laid.pane.left + fitted(laid, 'below-start', READING_AREA).shift).toBe(READING_AREA.left + ROOM);
	});

	it('opening above a control just under what is kept in sight over the area, opens below it, standing whole', () => {
		const fit = fitted(above(UNDER_THE_FILES_HEADER, MIDDLE, MEDIUM, QUESTION), 'above-end', READING_AREA);

		expect([fit.placement, fit.mostHeight >= QUESTION]).toEqual(['below-end', true]);
	});

	it('opening below a control near the foot of the reading area, opens above it, standing whole', () => {
		const fit = fitted(below(NEAR_THE_FOOT, MIDDLE, MEDIUM, QUESTION), 'below-end', READING_AREA);

		expect([fit.placement, fit.mostHeight >= QUESTION]).toEqual(['above-end', true]);
	});

	it('kept shorter where it was fitted before, opens the other way still, by how tall it stands whole', () => {
		const keptShort = { ...below(NEAR_THE_FOOT, MIDDLE, MEDIUM, ROOM), wholeHeight: QUESTION };

		expect(fitted(keptShort, 'below-end', READING_AREA).placement).toBe('above-end');
	});

	it('standing whole the way it opens, keeps that way, however much more room the other has', () => {
		expect(fitted(below(UNDER_THE_FILES_HEADER, MIDDLE, MEDIUM, QUESTION), 'below-start', READING_AREA).placement).toBe(
			'below-start'
		);
	});

	it('standing whole neither way, keeps the way it opens where that has the more room', () => {
		expect(fitted(below(UNDER_THE_FILES_HEADER, MIDDLE, MEDIUM, TALL), 'below-start', READING_AREA).placement).toBe(
			'below-start'
		);
	});
});
