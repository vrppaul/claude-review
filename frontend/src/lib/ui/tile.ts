/**
 * A tile (Tile): a mark on its colour's chip, square at the box's corner and
 * as tall as a small button, at the start of a card in a colour, so what the
 * card is about is seen before its words are read: the task a story begins
 * with, what was done, where to doubt it. Never said to a screen reader: the
 * words beside it say it. Its look is written in styles/ui.css.
 */

/**
 * Whose the card it starts is, or what it is, by its colour:
 * - reader: what the reader asked
 * - agent: what the agent did
 * - warning: what to look at
 */
export type TileTone = 'reader' | 'agent' | 'warning';

// The class of each tone in the library's stylesheet
export const TILE_TONES: Record<TileTone, string> = {
	reader: 'cr-ui-tile-reader',
	agent: 'cr-ui-tile-agent',
	warning: 'cr-ui-tile-warning'
};
