import { describe, it, expect } from 'vitest';
import { styleRules } from './stylesheets';

// A turn as a declaration writes it, and its angle: by the property that turns, about an axis or none, and by a
// function of a transform
const TURNS = [
	/(?:^|[;\s])rotate\s*:\s*(?:[xyz]\s+|(?:-?[\d.]+\s+){3})?(-?[\d.]+)(deg|turn|rad|grad)/g,
	/rotate[xyzXYZ]?\(\s*(-?[\d.]+)(deg|turn|rad|grad)\s*\)/g
];
// What each unit of an angle is in degrees
const DEGREES_IN: Record<string, number> = { deg: 1, turn: 360, rad: 180 / Math.PI, grad: 0.9 };
// A right angle, in degrees: a turn by a whole number of them points a chevron, and by none sets a square on its corner
const RIGHT_ANGLE = 90;
// How near a whole number of right angles a turn may be and still be one, in degrees: what writing it in another unit costs
const ROUNDING = 0.01;

/** Every angle a rule's declarations turn by, in degrees. */
function anglesOf(declarations: string): number[] {
	return TURNS.flatMap((turn) =>
		[...declarations.matchAll(turn)].map(([, angle, unit]) => Number(angle) * DEGREES_IN[unit])
	);
}

/** Whether a turn sets what it turns off the square, as a right angle and its multiples never do. */
function offTheSquare(degrees: number): boolean {
	return Math.abs(degrees - RIGHT_ANGLE * Math.round(degrees / RIGHT_ANGLE)) > ROUNDING;
}

// The selectors of every rule of the stylesheet that turns something off the square, however the turn is written
const turningOffTheSquare = styleRules()
	.filter(({ declarations }) => anglesOf(declarations).some(offTheSquare))
	.map(({ selectors }) => selectors);

/**
 * A pane points at the control it stands by, and a hanging card up at what
 * it is about, with an arrow: a square turned on its corner, on the ground
 * and in the edge of what it leaves. Drawn twice, the card's in literals of
 * its own, the two parted by a pixel; drawn once, they are one arrow. A
 * chevron is turned too, by right angles, to where it points; nothing else
 * the stylesheets draw is turned at all.
 */
describe('a square turned on its corner, the arrow of a pane and the tail of a card', () => {
	it('is drawn by one rule of the stylesheet', () => {
		expect(turningOffTheSquare).toHaveLength(1);
	});
});
