/**
 * A pane: what the reader opens from a control, what the page puts by one
 * as a note, and a modal. Each is drawn on one ground, edge, corner and lift
 * (styles/ui.css), at one of a few widths, headed alike where it is headed.
 *
 * A pane that stands by a control is placed beside it, lined up with one of
 * its edges, and then fitted into the window: moved along until it stands
 * whole inside it, no wider and no taller than the window leaves it room
 * for, its body scrolling inside. The window is measured as the pane opens
 * and again as it is resized or anything under the pane scrolls, so a pane
 * never keeps the room of a window it is no longer in.
 */

import type { Snippet } from 'svelte';
import type { Attachment } from 'svelte/attachments';

/**
 * What the control that opens a pane carries (Popover): spread on it, it says what it opens, opens it, and makes
 * the control known to the pane, which points at it and gives the keyboard back to it.
 */
export type TriggerProps = {
	'aria-haspopup': 'dialog';
	'aria-expanded': boolean;
	'aria-controls': string | undefined;
	onclick: () => void;
} & Record<symbol, Attachment<HTMLElement>>;

/** Where a pane opens beside what opened it, and which of its edges it lines up with. */
export type Placement = 'below-start' | 'below-end' | 'above-start' | 'above-end';

/** A box on the screen, in the window's pixels. */
export interface ScreenBox {
	left: number;
	right: number;
	top: number;
	bottom: number;
}

/** The window a pane is fitted into, in pixels. */
export interface WindowSize {
	width: number;
	height: number;
}

/** How a placement lays a pane out: its class in the library's stylesheet, and what follows from where it opens. */
interface Placing {
	drawnAs: string;
	/** Where its left edge stands at a width, lined up with the edge of what it stands by that it lines up with. */
	leftAt: (pane: ScreenBox, width: number) => number;
	/** The most it may reach from there, down to the window's foot or up to its top, less the room kept. */
	mostHeight: (pane: ScreenBox, window: WindowSize) => number;
}

// How far a pane stands from the window's edges at the least, in pixels
const ROOM = 8;

/** Lined up with its start, a pane keeps its left edge whatever its width. */
function keptStart(pane: ScreenBox): number {
	return pane.left;
}

/** Lined up with its end, a pane keeps its right edge, and its width is taken off that. */
function keptEnd(pane: ScreenBox, width: number): number {
	return pane.right - width;
}

/** Opening below, a pane reaches down from its top to the room above the window's foot. */
function downToTheFoot(pane: ScreenBox, window: WindowSize): number {
	return window.height - ROOM - pane.top;
}

/** Opening above, a pane reaches up from its foot to the room below the window's top. */
function upToTheTop(pane: ScreenBox): number {
	return pane.bottom - ROOM;
}

const PLACINGS: Record<Placement, Placing> = {
	'below-start': { drawnAs: 'cr-ui-below-start', leftAt: keptStart, mostHeight: downToTheFoot },
	'below-end': { drawnAs: 'cr-ui-below-end', leftAt: keptEnd, mostHeight: downToTheFoot },
	'above-start': { drawnAs: 'cr-ui-above-start', leftAt: keptStart, mostHeight: upToTheTop },
	'above-end': { drawnAs: 'cr-ui-above-end', leftAt: keptEnd, mostHeight: upToTheTop }
};

/** The class a placement is drawn with. */
export function placedAs(placement: Placement): string {
	return PLACINGS[placement].drawnAs;
}

/**
 * How wide a pane is drawn, and so what it holds:
 * - medium: rows — controls, keys, things to pick
 * - wide: what was written — replies, comments, a question that shows what it asks about
 * - fitted: as wide as what it holds and no wider — a note, a question, a drawing
 * - along: as wide as what it stands over — the list of what a field can point at
 */
export type PaneWidth = 'medium' | 'wide' | 'fitted' | 'along';

export const PANE_WIDTHS: Record<PaneWidth, string> = {
	medium: 'cr-ui-pane-medium',
	wide: 'cr-ui-pane-wide',
	fitted: 'cr-ui-pane-fitted',
	along: 'cr-ui-pane-along'
};

/** What a pane says by its edge: that it speaks for the agent, or of what it brought that is not read yet. */
export type PaneEdge = 'agent' | 'unread';

export const PANE_EDGES: Record<PaneEdge, string> = { agent: 'cr-ui-pane-agent', unread: 'cr-ui-pane-unread' };

/** What heads a pane: what it is called, and the way to put it away; and what stands beside its name, if anything. */
export interface PaneHead {
	heading: string;
	close: () => void;
	/** What its close says it does, where that is more than closing the pane: "Close for now". */
	closing?: string | undefined;
	aside?: Snippet | undefined;
}

// Where along a control a pane's arrow points: its middle
const MIDDLE = 0.5;

/**
 * How a pane is fitted into the window: how far it is moved along from where
 * it lines up, and the most it may be drawn across and down.
 */
export interface PaneFit {
	shift: number;
	mostWidth: number;
	mostHeight: number;
}

/**
 * How far in from the edge a pane lines up with its arrow points, in pixels: to the middle of the control it
 * stands by. None while the control is not drawn yet.
 */
export function arrowOffsetTo(control: HTMLElement | undefined): number {
	return control ? control.offsetWidth * MIDDLE : 0;
}

/**
 * Where a pane stands as its placement lays it out, before it is moved
 * along: what it is placed in, and where in that, neither changed by the
 * move.
 */
export function laidOut(pane: HTMLElement): ScreenBox {
	const placedIn = pane.offsetParent?.getBoundingClientRect() ?? new DOMRect();
	const left = placedIn.left + pane.offsetLeft;
	const top = placedIn.top + pane.offsetTop;
	return { left, right: left + pane.offsetWidth, top, bottom: top + pane.offsetHeight };
}

/**
 * Fit a pane laid out as its placement puts it into the window. It is no
 * wider than the window less its room either side; lined up with an end, it
 * keeps that edge as it narrows. Then it is moved along as little as stands
 * it whole inside, or to the room from the left edge where it cannot. It
 * reaches down to the room above the window's foot, or up to the room below
 * its top.
 */
export function fitted(pane: ScreenBox, placement: Placement, window: WindowSize): PaneFit {
	const { leftAt, mostHeight } = PLACINGS[placement];
	const mostWidth = window.width - ROOM - ROOM;
	const width = Math.min(pane.right - pane.left, mostWidth);
	const left = leftAt(pane, width);
	const shift = Math.max(ROOM, Math.min(left, window.width - ROOM - width)) - left;
	return { shift, mostWidth, mostHeight: mostHeight(pane, window) };
}
