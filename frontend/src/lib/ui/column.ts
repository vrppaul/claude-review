/**
 * A column beside what is read (SideColumn): the tree of files or a story's
 * contents on the left, the agent's panel on the right. Each as wide as the
 * reader left it, sized by its grip on the edge facing what is read, and on
 * a screen too narrow to keep it beside that, lying over it. Each is put
 * away alike, narrowed to a rail where it stood that says what is behind
 * it, its toggle at the outer edge on one spot open and put away. Its look
 * is written in styles/ui.css.
 */

import type { ColumnWidth, Grows } from '$lib/dom/resize';
import type { IconName } from './icons';

/** Which side of what is read a column stands on. */
export type ColumnSide = 'left' | 'right';

/** How a column of a side is drawn, the toggle at the side's outer edge drawing the state the column is in. */
interface SideDrawn {
	/** Its class in the library's stylesheet. */
	drawnAs: string;
	/** The way it grows: towards its grip, on the edge facing what is read. */
	grows: Grows;
	/** Whether its toggle leads its head, the outer edge being the head's start. */
	toggleLeads: boolean;
	/** What its toggle draws while it stands open, and while it is put away. */
	open: IconName;
	putAway: IconName;
}

export const COLUMN_SIDES: Record<ColumnSide, SideDrawn> = {
	left: {
		drawnAs: 'cr-ui-side-column-left',
		grows: 'right',
		toggleLeads: true,
		open: 'column-left-open',
		putAway: 'column-left-put-away'
	},
	right: {
		drawnAs: 'cr-ui-side-column-right',
		grows: 'left',
		toggleLeads: false,
		open: 'column-right-open',
		putAway: 'column-right-put-away'
	}
};

/**
 * What a column holds, and so how it is laid out under its head:
 * - list: rows to go through, scrolled as one with room round them
 * - parts: parts that lay themselves out and scroll where they scroll, as the panel's conversation does
 */
export type ColumnHolds = 'list' | 'parts';

// The class of each in the library's stylesheet
export const COLUMN_HOLDS: Record<ColumnHolds, string> = {
	list: 'cr-scroller cr-ui-column-list',
	parts: 'cr-ui-column-parts'
};

/** A column the reader puts away and brings back, as well as sizes. */
export interface PutAway extends ColumnWidth {
	/** Whether it is on screen. */
	readonly open: boolean;
	/** Whether the reader made the last change to that: only then does it move, since nothing moves by itself. */
	readonly changedByReader: boolean;
	toggle: () => void;
}
