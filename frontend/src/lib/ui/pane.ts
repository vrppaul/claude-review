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
 * and the other has more room (a pane drawn before it knows what it will
 * hold opens the way with more room), is moved along until it stands whole inside,
 * and is drawn no wider and no taller than that leaves it room for, its body
 * scrolling inside. What it is seen in is measured as it opens and again as the
 * window is resized, a box it is seen in changes size, or anything under
 * the pane scrolls, so a pane never keeps the room of a place it is no
 * longer in; a pane whose way is chosen as it opens scrolls with what it
 * stands by instead, and keeps its way.
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

/** A way a pane opens beside what opened it, and which of its edges it lines up with. */
export type Way = 'below-start' | 'below-end' | 'above-start' | 'above-end';

/**
 * Where a pane opens: a way, or, for a pane drawn before it knows what it
 * will hold, lined up with the start on whichever side has more room as it
 * opens, so neither what it comes to hold nor what scrolls under it moves
 * it to the other side.
 */
export type Placement = Way | 'roomier-start';

/**
 * How a placement chooses the way a pane opens: the way it opens first;
 * whether it keeps to it where it stands whole, which only a pane that
 * knows what it holds as it is drawn can tell; and whether the way is
 * chosen once, as the pane opens, the pane then scrolling with what it
 * stands by as a card in the code does, fitted again only to a window resized.
 */
interface Opening {
	way: Way;
	keptWhereWhole: boolean;
	chosenAsItOpens: boolean;
}

const OPENINGS: Record<Placement, Opening> = {
	'below-start': { way: 'below-start', keptWhereWhole: true, chosenAsItOpens: false },
	'below-end': { way: 'below-end', keptWhereWhole: true, chosenAsItOpens: false },
	'above-start': { way: 'above-start', keptWhereWhole: true, chosenAsItOpens: false },
	'above-end': { way: 'above-end', keptWhereWhole: true, chosenAsItOpens: false },
	'roomier-start': { way: 'below-start', keptWhereWhole: false, chosenAsItOpens: true }
};

/**
 * Something a pane stands by where no control holds it, a stretch of text:
 * where it stands in the window, read each time it is asked; null while it
 * is not drawn, when the pane stays where it last stood.
 */
export type Spot = () => DOMRectReadOnly | null;

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

/** How a way lays a pane out: its class in the library's stylesheet, and what follows from where it opens. */
interface Placing {
	drawnAs: string;
	/** Where its left edge stands at a width, lined up with the edge of what it stands by that it lines up with. */
	leftAt: (pane: ScreenBox, width: number) => number;
	/** The way that lines up with the same edge and opens the other way. */
	otherWay: Way;
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

const PLACINGS: Record<Way, Placing> = {
	'below-start': { drawnAs: 'cr-ui-below-start', leftAt: keptStart, otherWay: 'above-start', roomFrom: downToTheFoot },
	'below-end': { drawnAs: 'cr-ui-below-end', leftAt: keptEnd, otherWay: 'above-end', roomFrom: downToTheFoot },
	'above-start': { drawnAs: 'cr-ui-above-start', leftAt: keptStart, otherWay: 'below-start', roomFrom: upToTheTop },
	'above-end': { drawnAs: 'cr-ui-above-end', leftAt: keptEnd, otherWay: 'below-end', roomFrom: upToTheTop }
};

/** The class a placement is drawn with: that of the way it opens first. */
export function placedAs(placement: Placement): string {
	return PLACINGS[OPENINGS[placement].way].drawnAs;
}

/**
 * How wide a pane is drawn, and so what it holds:
 * - medium: rows — controls, keys, things to pick
 * - wide: what was written — replies, comments, a question that shows what it asks about
 * - code: lines of code, each read whole to its way to where it stands — where a name is defined and used
 * - fitted: as wide as what it holds and no wider — a note, a question, a drawing
 * - along: as wide as what it stands over — the list of what a field can point at
 */
export type PaneWidth = 'medium' | 'wide' | 'code' | 'fitted' | 'along';

export const PANE_WIDTHS: Record<PaneWidth, string> = {
	medium: 'cr-ui-pane-medium',
	wide: 'cr-ui-pane-wide',
	code: 'cr-ui-pane-code',
	fitted: 'cr-ui-pane-fitted',
	along: 'cr-ui-pane-along'
};

/**
 * What a pane says by its edge: that it speaks for the agent, invites the reader's own word, speaks of what the agent
 * brought that is not read yet, or of what failed.
 */
export type PaneEdge = 'agent' | 'reader' | 'unread' | 'failure';

export const PANE_EDGES: Record<PaneEdge, string> = {
	agent: 'cr-ui-pane-agent',
	reader: 'cr-ui-pane-reader',
	unread: 'cr-ui-pane-unread',
	failure: 'cr-ui-pane-failure'
};

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
	/** The way it opens, as its placement chooses. */
	placement: Way;
	shift: number;
	mostWidth: number;
	mostHeight: number;
}

/**
 * How far in from the edge a pane lines up with its arrow points, in pixels: to the middle of the control it
 * stands by. None while the control is not drawn yet.
 */
export function arrowOffsetTo(control: HTMLElement | undefined): number {
	return control ? arrowOffsetAlong(control.offsetWidth) : 0;
}

/** How far in from the edge a pane lines up with its arrow points, in pixels, along what it stands by so wide. */
export function arrowOffsetAlong(width: number): number {
	return width * MIDDLE;
}

/** A number of pixels as the stylesheet takes it, or none where there is no number: before a pane is measured. */
export function pixels(measured: number | undefined): string | undefined {
	return measured === undefined ? undefined : `${measured}px`;
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

/** Whether a pane is fitted again as anything under it scrolls: unless its way was chosen as it opened. */
export function fittedAsItScrolls(placement: Placement): boolean {
	return !OPENINGS[placement].chosenAsItOpens;
}

/**
 * The way a pane opens: the way it opened already where its placement
 * chooses once; else the way its placement opens first, unless the other
 * way has more room and the pane would not stand whole its first way, or
 * cannot tell whether it would.
 */
function openedWay(laid: LaidOut, placement: Placement, offBy: number, seen: ScreenBox, before: Way | null): Way {
	const { way, keptWhereWhole, chosenAsItOpens } = OPENINGS[placement];
	if (chosenAsItOpens && before !== null) return before;
	const { otherWay, roomFrom } = PLACINGS[way];
	const room = roomFrom(laid.standsBy, offBy, seen);
	const roomTheOtherWay = PLACINGS[otherWay].roomFrom(laid.standsBy, offBy, seen);
	const keptWhole = keptWhereWhole && laid.wholeHeight <= room;
	return !keptWhole && roomTheOtherWay > room ? otherWay : way;
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
 *
 * @param before the way it opened at its last fit while it has stood open; none as it opens
 */
export function fitted(laid: LaidOut, placement: Placement, seen: ScreenBox, before: Way | null): PaneFit {
	const offBy = standsOffBy(laid);
	const opened = openedWay(laid, placement, offBy, seen, before);
	const { leftAt, roomFrom } = PLACINGS[opened];
	const mostWidth = seen.right - seen.left - ROOM - ROOM;
	const width = Math.min(laid.pane.right - laid.pane.left, mostWidth);
	const left = leftAt(laid.pane, width);
	const shift = Math.max(seen.left + ROOM, Math.min(left, seen.right - ROOM - width)) - left;
	return { placement: opened, shift, mostWidth, mostHeight: roomFrom(laid.standsBy, offBy, seen) };
}
