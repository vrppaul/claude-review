/**
 * A frame with an edge at its start (EdgeFrame): words set apart from what
 * stands around them by a line down their start, in the colour of whose
 * they are or what they are, on that colour's wash or on what is under them.
 * One radius for every one, and one room round what it holds.
 *
 * A band (Band) is a block of a frame's words the reader may ask about: lit
 * across its frame from inside the frame's edge to its far side, it reaches
 * past its words into the room the frame keeps round them, on every side,
 * taking none, so its words stand where a frame's words would without it; and
 * it offers its act over its top right edge while it is lit. A block in a
 * frame of its own draws that frame itself; what hangs under the block hangs
 * from where its band ends.
 *
 * A block may stand in no frame, its words on the edge of the part it stands
 * in, as a chapter's why does: its band reaches past them either side as far
 * as a card stands its words in, taking none of that room, and above and
 * below as far as a band reaches, taking that room, so it stands that far
 * from what is round it; it offers its act over its top right edge, as a
 * band in a frame does. What hangs under it is as wide as its band.
 *
 * A block may stand on a card of its own instead (Card, washed): one line of
 * what a story says in short, on the wash of whose it is. Its band fills the
 * card, lit to the card's edge, and offers its act inside the card's top
 * right corner. Blocks one under another (Bands) stand as close as cards in
 * a stack, whichever they are.
 *
 * Or it may be an item of a list on a card of lists (ListsCardRow), on no
 * frame of its own: its light a pill round its words, reaching a step and a
 * half past them above and below and two to either side and taking none of
 * that room; its offer in a column of its own beside the words, kept while
 * unseen, so no word moves as it shows. What hangs under it is as wide as
 * that light.
 *
 * The frame, the card, the band and their stack are drawn together here and
 * in the library's stylesheet, so nothing outside the library lays out round
 * them.
 */

import type { WashedTone } from './card';

/**
 * Whose or what the framed words are, and the ground the tone lays:
 * - agent: what the agent says in a story; on its tint
 * - warning: what the review warns about, what a story costs; on its tint
 */
export type FrameTone = 'agent' | 'warning';

/** Whether the frame lays its tone's ground under the words, or stands them on what is under it. */
export type FrameGround = 'tint' | 'none';

/** A frame with an edge at its start: whose its words are, and whether it lays their colour's ground. */
export interface EdgeLook {
	shape: 'edge';
	tone: FrameTone;
	ground: FrameGround;
}

/** Words in no frame, on the edge of the part they stand in. */
interface UnframedLook {
	shape: 'unframed';
}

/** A card of a block's own, washed in its tone: whose the block is, or that it is what to look at. */
interface CardLook {
	shape: 'card';
	tone: WashedTone;
}

/** An item of a list on a card of lists, which stands its words in no frame of its own. */
interface ListedLook {
	shape: 'listed';
}

/** How a frame is drawn: for whoever hands one on, as a block of a story hands on the frame its words stand in. */
export type FrameLook = EdgeLook | UnframedLook | CardLook | ListedLook;

// The class of each tone, and of a ground, in the library's stylesheet
export const FRAME_TONES: Record<FrameTone, string> = {
	agent: 'cr-ui-frame-agent',
	warning: 'cr-ui-frame-warning'
};

export const FRAME_GROUNDS: Record<FrameGround, string | null> = { tint: 'cr-ui-frame-tinted', none: null };

// The class of a band (Band) by where its words stand, in the library's stylesheet: one inside an edge frame is
// drawn as a band is
export const BANDS_BY_FRAME: Record<FrameLook['shape'], string | null> = {
	edge: null,
	unframed: 'cr-ui-band-unframed',
	card: 'cr-ui-band-on-a-card',
	listed: 'cr-ui-band-listed'
};
