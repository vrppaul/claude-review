/**
 * A pane: what the reader opens from a control, what the page puts by one
 * as a note, and a modal. Each is drawn on one ground, edge, corner and lift
 * (styles/ui.css), at one of a few widths, headed alike where it is headed.
 *
 * A pane that stands by a control is placed beside it, lined up with one of
 * its edges, and then fitted into what the reader sees where it is drawn:
 * the window, or the part of a reading area under what is kept in sight at
 * its top, which lies over the pane, and above the area's foot, which cuts
 * it off. It opens the other way where it would not stand whole its own way
 * and the other has more room, is moved along until it stands whole inside,
 * and is drawn no wider and no taller than that leaves it room for, its body
 * scrolling inside. What it is seen in is measured as it opens and again as the
 * window is resized or anything under the pane scrolls, so a pane never
 * keeps the room of a place it is no longer in.
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

/**
 * A pane as it is drawn, before it is fitted: the box of what it stands by,
 * its own box beside that, and how tall it stands whole — as tall as it is
 * drawn, and as much again as what it holds scrolls past that where it was
 * drawn shorter.
 */
export interface LaidOut {
	standsBy: ScreenBox;
	pane: ScreenBox;
	wholeHeight: number;
}

/** How a placement lays a pane out: its class in the library's stylesheet, and what follows from where it opens. */
interface Placing {
	drawnAs: string;
	/** Where its left edge stands at a width, lined up with the edge of what it stands by that it lines up with. */
	leftAt: (pane: ScreenBox, width: number) => number;
	/** The placement that lines up with the same edge and opens the other way. */
	otherWay: Placement;
	/**
	 * The most it may reach, standing so far off what it stands by: down to the foot of what it is seen in, or
	 * up to its top, less the room kept.
	 */
	roomFrom: (standsBy: ScreenBox, offBy: number, seen: ScreenBox) => number;
}

// How far a pane stands from the edges of what it is seen in at the least, in pixels
const ROOM = 8;

/** Lined up with its start, a pane keeps its left edge whatever its width. */
function keptStart(pane: ScreenBox): number {
	return pane.left;
}

/** Lined up with its end, a pane keeps its right edge, and its width is taken off that. */
function keptEnd(pane: ScreenBox, width: number): number {
	return pane.right - width;
}

/** Opening below, a pane reaches down from under what it stands by to the room above the foot of what it is seen in. */
function downToTheFoot(standsBy: ScreenBox, offBy: number, seen: ScreenBox): number {
	return seen.bottom - ROOM - (standsBy.bottom + offBy);
}

/** Opening above, a pane reaches up from over what it stands by to the room below the top of what it is seen in. */
function upToTheTop(standsBy: ScreenBox, offBy: number, seen: ScreenBox): number {
	return standsBy.top - offBy - (seen.top + ROOM);
}

const PLACINGS: Record<Placement, Placing> = {
	'below-start': { drawnAs: 'cr-ui-below-start', leftAt: keptStart, otherWay: 'above-start', roomFrom: downToTheFoot },
	'below-end': { drawnAs: 'cr-ui-below-end', leftAt: keptEnd, otherWay: 'above-end', roomFrom: downToTheFoot },
	'above-start': { drawnAs: 'cr-ui-above-start', leftAt: keptStart, otherWay: 'below-start', roomFrom: upToTheTop },
	'above-end': { drawnAs: 'cr-ui-above-end', leftAt: keptEnd, otherWay: 'below-end', roomFrom: upToTheTop }
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
 * How a pane is fitted into what it is seen in: the way it opens, how far it
 * is moved along from where it lines up, and the most it may be drawn across
 * and down.
 */
export interface PaneFit {
	/** Its own placement, or the one that opens the other way, where it would not stand whole its own way. */
	placement: Placement;
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
 * Where a pane stands as it is drawn, before it is moved along: what it is
 * placed in, which is what it stands by, and where in that, neither changed
 * by the move; and how tall it stands whole, its body holding all it holds.
 */
export function laidOut(pane: HTMLElement, body: HTMLElement): LaidOut {
	const standsBy = pane.offsetParent?.getBoundingClientRect() ?? new DOMRect();
	const left = standsBy.left + pane.offsetLeft;
	const top = standsBy.top + pane.offsetTop;
	return {
		standsBy,
		pane: { left, right: left + pane.offsetWidth, top, bottom: top + pane.offsetHeight },
		wholeHeight: pane.offsetHeight + body.scrollHeight - body.clientHeight
	};
}

/** How far a pane stands off what it stands by, below it or above it: the room its arrow takes. */
function standsOffBy({ standsBy, pane }: LaidOut): number {
	return Math.max(pane.top - standsBy.bottom, standsBy.top - pane.bottom);
}

/**
 * The way a pane opens: the way its placement says, unless it would not
 * stand whole there and the other way has more room.
 */
function openedWay(laid: LaidOut, placement: Placement, offBy: number, seen: ScreenBox): Placement {
	const { otherWay, roomFrom } = PLACINGS[placement];
	const room = roomFrom(laid.standsBy, offBy, seen);
	const roomTheOtherWay = PLACINGS[otherWay].roomFrom(laid.standsBy, offBy, seen);
	return laid.wholeHeight > room && roomTheOtherWay > room ? otherWay : placement;
}

/**
 * Fit a pane into what it is seen in, from where it is drawn: whichever way
 * that is, it says the same of what the pane stands by, how far off it, how
 * wide and how tall the pane is. It opens the way it has the room for. It is
 * no wider than what it is seen in less its room either side; lined up with
 * an end, it keeps that edge as it narrows. Then it is moved along as little
 * as stands it whole inside, or to the room from the left edge where it
 * cannot. It reaches down to the room above the foot of what it is seen in,
 * or up to the room below its top.
 */
export function fitted(laid: LaidOut, placement: Placement, seen: ScreenBox): PaneFit {
	const offBy = standsOffBy(laid);
	const opened = openedWay(laid, placement, offBy, seen);
	const { leftAt, roomFrom } = PLACINGS[opened];
	const mostWidth = seen.right - seen.left - ROOM - ROOM;
	const width = Math.min(laid.pane.right - laid.pane.left, mostWidth);
	const left = leftAt(laid.pane, width);
	const shift = Math.max(seen.left + ROOM, Math.min(left, seen.right - ROOM - width)) - left;
	return { placement: opened, shift, mostWidth, mostHeight: roomFrom(laid.standsBy, offBy, seen) };
}
