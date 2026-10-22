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
 * from where its band ends. Blocks one under another (Bands) stand as far
 * apart as that offer is tall, so it lies over none of the words above it.
 *
 * A block may stand on a card of its own instead (Card, washed): one line of
 * what a story says in short, on the wash of whose it is. Its band fills the
 * card, lit to the card's edge, and offers its act inside the card's top
 * right corner; cards one under another stand as close as cards in a stack.
 *
 * The frame, the card, the band and their stack are drawn together here and
 * in the library's stylesheet, so nothing outside the library lays out round
 * them.
 */

import type { WashedTone } from './card';

/**
 * Whose or what the framed words are, and the ground the tone lays:
 * - agent: what the agent says in a story; on its tint
 * - warning: what the review warns about, where to doubt it, what it costs;
 *   on its tint
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

/** A card of a block's own, washed in its tone: whose the block is, or that it is what to look at. */
interface CardLook {
	shape: 'card';
	tone: WashedTone;
}

/** How a frame is drawn: for whoever hands one on, as a block of a story hands on the frame its words stand in. */
export type FrameLook = EdgeLook | CardLook;

// The class of each tone, and of a ground, in the library's stylesheet
export const FRAME_TONES: Record<FrameTone, string> = {
	agent: 'cr-ui-frame-agent',
	warning: 'cr-ui-frame-warning'
};

export const FRAME_GROUNDS: Record<FrameGround, string | null> = { tint: 'cr-ui-frame-tinted', none: null };
