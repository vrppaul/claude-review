/**
 * What a button is to the reader beside its neighbours, and how tall it
 * stands: each a class of the library's stylesheet (styles/ui.css), where
 * its look is written from the tokens.
 *
 * A button of the page is one of these, drawn by `Button` or `IconButton`,
 * and nothing outside the library lays a look over it: a look the page needs
 * is a tone or a size here, with the reason a reader needs it. The acts that
 * end a pane, a card, a question, a field being written, a note or a view's
 * wait stand in one row, `Actions`, the act it leads to last.
 */

import type { Snippet } from 'svelte';

/**
 * - primary: the one act a pane, a card, a field, a note or a wait leads to,
 *   filled with the control's blue.
 * - quiet: an act that must not outweigh the words beside it, or the main
 *   act it stands beside in a row of acts.
 * - secondary: an act on what is read — a thread, a block of the story's
 *   words — which would read as part of it were it quiet: edged, on the
 *   page's own ground.
 * - asking: asking the agent about what is read, the secondary's act in
 *   the reader's own blue, edge and words: what they ask is theirs, as every
 *   control of theirs is drawn in it.
 * - danger: the act that loses what was written, once it was asked, filled
 *   with the colour of what destroys, so it is never taken for the safe
 *   answer beside it.
 * - marked: something of the reader's own to look at, or what they narrowed
 *   the review to, on their mark's tint.
 */
export type ButtonTone = 'primary' | 'quiet' | 'secondary' | 'asking' | 'danger' | 'marked';

/** xs among words and small controls, 24 pixels; sm in a row of acts and where it ends a bar, 32 pixels. */
export type ButtonSize = 'xs' | 'sm';

// The classes of each tone; a filled one (primary, danger) is drawn over its own way under the pointer and open
export const BUTTON_TONES: Record<ButtonTone, string> = {
	primary: 'cr-ui-primary cr-ui-filled',
	quiet: 'cr-ui-quiet',
	secondary: 'cr-ui-secondary',
	asking: 'cr-ui-asking',
	danger: 'cr-ui-danger cr-ui-filled',
	marked: 'cr-ui-marked'
};

export const BUTTON_SIZES: Record<ButtonSize, string> = { xs: 'cr-ui-xs', sm: 'cr-ui-sm' };

/**
 * - square: an icon alone, as tall as it is wide.
 * - notification: a mark with a figure on its corner, how many of what it
 *   opens wait: a button's room either side of its icon, so the figure
 *   stands over its edge and not over the icon, and as wide with no figure
 *   on it as with one, the figure a Count handed to it while there is one.
 *   A square has no corner to hold one, so it is handed none.
 */
export type IconButtonShaped =
	| { shape: 'square'; corner?: never }
	| { shape: 'notification'; corner: Snippet | undefined };
export type IconButtonShape = IconButtonShaped['shape'];

export const ICON_BUTTON_SHAPES: Record<IconButtonShape, string> = {
	square: 'cr-ui-icon-button',
	notification: 'cr-ui-notification'
};
