import { describe, it, expect } from 'vitest';
import { fitted, type ScreenBox } from '$lib/ui/pane';

// A phone's window, and the room a pane keeps from its edges
const PHONE = { width: 420, height: 800 };
const ROOM = 8;
// A pane of rows, as wide as the library draws one, and how tall a pane laid out under the header stands
const MEDIUM = 320;
const TALL = 650;
// Where the header's controls stand: one at the far left, one in the middle, and how far down the header ends
const FAR_LEFT = 20;
const MIDDLE = 150;
const UNDER_THE_HEADER = 48;

/** A pane laid out with its left edge at a place, under the header, at a width and a height. */
function laidOutAt(left: number, width: number, height: number): ScreenBox {
	return { left, right: left + width, top: UNDER_THE_HEADER, bottom: UNDER_THE_HEADER + height };
}

describe('a pane fitted into the window', () => {
	it('stays where it lines up while it stands whole inside the window', () => {
		expect(fitted(laidOutAt(ROOM, MEDIUM, TALL), 'below-start', PHONE).shift).toBe(0);
	});

	it('lined up with the end of a control near the left edge, moves right to the room kept from that edge', () => {
		const pane = laidOutAt(FAR_LEFT - MEDIUM, MEDIUM, TALL);

		expect(pane.left + fitted(pane, 'below-end', PHONE).shift).toBe(ROOM);
	});

	it('lined up with the start of a control in the middle, moves left until its right edge keeps the room', () => {
		const pane = laidOutAt(MIDDLE, MEDIUM, TALL);

		expect(pane.right + fitted(pane, 'below-start', PHONE).shift).toBe(PHONE.width - ROOM);
	});

	it('is no wider than the window less the room either side, and keeps the end it lines up with as it narrows', () => {
		const wider = PHONE.width;
		const pane = laidOutAt(0, wider, TALL);
		const fit = fitted(pane, 'below-end', PHONE);

		expect([fit.mostWidth, pane.right - fit.mostWidth + fit.shift]).toEqual([PHONE.width - 2 * ROOM, ROOM]);
	});

	it('opening below, reaches down no further than the room above the window foot', () => {
		expect(fitted(laidOutAt(ROOM, MEDIUM, TALL), 'below-start', PHONE).mostHeight).toBe(
			PHONE.height - ROOM - UNDER_THE_HEADER
		);
	});

	it('opening above, reaches up no further than the room below the window top', () => {
		const pane = laidOutAt(ROOM, MEDIUM, TALL);

		expect(fitted(pane, 'above-start', PHONE).mostHeight).toBe(pane.bottom - ROOM);
	});
});
