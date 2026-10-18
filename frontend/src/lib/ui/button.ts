/**
 * What a button is to the reader beside its neighbours, and how tall it
 * stands: each a class of the library's stylesheet (styles/ui.css), where
 * its look is written from the tokens.
 *
 * A button of the page is one of these, drawn by `Button` or `IconButton`,
 * and nothing outside the library lays a look over it: a look the page needs
 * is a tone or a size here, with the reason a reader needs it.
 */

/**
 * - primary: the one act a pane, a card or a field leads to, filled with the
 *   control's blue.
 * - quiet: an act that must not outweigh the words beside it.
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

/** xs among words and small controls, 24 pixels; sm where it ends a pane, a card or a bar, 32 pixels. */
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
