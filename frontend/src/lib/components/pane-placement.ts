/** Where a pane opens beside what opened it, and which of its edges it lines up with. */
export type Placement = 'below-start' | 'below-end' | 'above-start';

// Where along a control a pane's arrow points: its middle
const MIDDLE = 0.5;

/**
 * How far in from the edge a pane lines up with its arrow points, in pixels: to the middle of the control it
 * stands by. None while the control is not drawn yet.
 */
export function arrowOffsetTo(control: HTMLElement | undefined): number {
	return control ? control.offsetWidth * MIDDLE : 0;
}
