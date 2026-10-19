/**
 * A column beside what is read (Column): the tree of files and a story's
 * contents on the left, put away to a rail where they stood (SideColumn);
 * the agent's panel on the right. Each as wide as the reader left it, sized
 * by its grip on the edge facing what is read, and on a screen too narrow to
 * keep it beside that, lying over it. Its look is written in styles/ui.css.
 */

import type { ColumnWidth, Grows } from '$lib/dom/resize';

/** Which side of what is read a column stands on. */
export type ColumnSide = 'left' | 'right';

/** How a column of each side is drawn: its class in the library's stylesheet, and the way it grows, towards its grip. */
export const COLUMN_SIDES: Record<ColumnSide, { drawnAs: string; grows: Grows }> = {
	left: { drawnAs: 'cr-ui-column-left', grows: 'right' },
	right: { drawnAs: 'cr-ui-column-right', grows: 'left' }
};

/** A column the reader puts away and brings back, as well as sizes. */
export interface PutAway extends ColumnWidth {
	/** Whether it is on screen. */
	readonly open: boolean;
	toggle: () => void;
}
