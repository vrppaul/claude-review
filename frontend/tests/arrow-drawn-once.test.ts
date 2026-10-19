import { describe, it, expect } from 'vitest';
import { styleRules } from './stylesheets';

// How a rule turns a square onto its corner, by the property that turns it or by a transform
const TURNED_ON_ITS_CORNER = /(?:^|[;\s])(?:rotate:\s*45deg|transform:\s*rotate\(45deg\))\s*;/;

// The selectors of every rule of the stylesheet that turns a square onto its corner
const turningOnACorner = styleRules()
	.filter(({ declarations }) => TURNED_ON_ITS_CORNER.test(declarations.replaceAll('\n', ' ')))
	.map(({ selectors }) => selectors);

/**
 * A pane points at the control it stands by, and a hanging card up at what
 * it is about, with an arrow: a square turned on its corner, on the ground
 * and in the edge of what it leaves. Drawn twice, the card's in literals of
 * its own, the two parted by a pixel; drawn once, they are one arrow.
 */
describe('a square turned on its corner, the arrow of a pane and the tail of a card', () => {
	it('is drawn by one rule of the stylesheet', () => {
		expect(turningOnACorner).toHaveLength(1);
	});
});
