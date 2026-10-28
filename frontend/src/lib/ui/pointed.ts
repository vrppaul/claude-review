/**
 * Where the name of a part the reader points at stands (PointedRing):
 * under the part, where the window leaves room for it there; over it where
 * it does not; and inside the part's foot where the part fills the window,
 * as code taller than the window does. Always inside the window, lined up
 * with the part's left edge as far as the window allows.
 */

/** A box in the window, in pixels. */
interface Box {
	left: number;
	top: number;
	width: number;
	height: number;
}

/** How large a thing is drawn, in pixels. */
interface Size {
	width: number;
	height: number;
}

/** Where a name stands in the window, in pixels from its top left. */
export interface NamePlace {
	left: number;
	top: number;
}

// How far the name stands from the part it names, and from the window's edges, at the least, in pixels
const OFF_THE_PART = 4;
const OFF_THE_EDGE = 8;

/** A number kept between two others. */
function keptBetween(value: number, least: number, most: number): number {
	return Math.max(least, Math.min(value, most));
}

/** Where the name of a part stands: under it, over it, or in its foot, inside the window. */
export function namePlace(part: Box, name: Size, window: Size): NamePlace {
	const lowest = window.height - OFF_THE_EDGE - name.height;
	const under = part.top + part.height + OFF_THE_PART;
	const over = part.top - OFF_THE_PART - name.height;
	const inItsFoot = Math.min(part.top + part.height, window.height) - OFF_THE_PART - name.height;
	const top = under <= lowest ? under : over >= OFF_THE_EDGE ? over : inItsFoot;
	return {
		left: keptBetween(part.left, OFF_THE_EDGE, window.width - OFF_THE_EDGE - name.width),
		top: keptBetween(top, OFF_THE_EDGE, lowest)
	};
}
