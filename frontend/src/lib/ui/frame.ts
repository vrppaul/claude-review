/**
 * A frame with an edge at its start (EdgeFrame): words set apart from what
 * stands around them by a line down their start, in the colour of whose
 * they are or what they are, on that colour's wash or on what is under them.
 * One radius for every one, and room of its own round what it holds, which
 * says where the room is taken: round its words, or inside the bands of the
 * blocks it holds that the reader may ask about.
 */

/**
 * Whose or what the framed words are, and the ground the tone lays:
 * - reader: a thread of the reader's folded away; on the raised surface, as
 *   their mark's own wash is the tint of the one they are at
 * - agent: what the agent says, in a story or in a thread it raised; on its
 *   wash
 * - warning: what the review warns about, where to doubt it, what it costs;
 *   on its wash
 * - quiet: something settled, stepping back; on the raised surface
 * - stale: a copy of lines a thread has lost; on the page's own ground,
 *   inside the card
 */
export type FrameTone = 'reader' | 'agent' | 'warning' | 'quiet' | 'stale';

/** Whether the frame lays its tone's ground under the words, or stands them on what is under it. */
export type FrameGround = 'tint' | 'none';

/**
 * What a frame holds, which says where its room is taken:
 * - words: it stands them in from its edge and its far side, and above and
 *   below them
 * - bands: blocks the reader may ask about, each lit as a band from inside
 *   the frame's edge to its far side, which take that room inside the band;
 *   the frame keeps the room above and below what it holds, which a band
 *   reaches into past its words
 */
export type FrameHolds = 'words' | 'bands';

/** How a frame is drawn: for whoever hands one on, as a block of a story hands on the frame its words stand in. */
export interface FrameLook {
	tone: FrameTone;
	ground: FrameGround;
	/** Its edge broken: words read out of the code, not said by whoever made it. */
	dashed?: boolean | undefined;
}

// The class of each tone, of a ground, and of the room for what a frame holds, in the library's stylesheet
export const FRAME_TONES: Record<FrameTone, string> = {
	reader: 'cr-ui-frame-reader',
	agent: 'cr-ui-frame-agent',
	warning: 'cr-ui-frame-warning',
	quiet: 'cr-ui-frame-quiet',
	stale: 'cr-ui-frame-stale'
};

export const FRAME_GROUNDS: Record<FrameGround, string | null> = { tint: 'cr-ui-frame-tinted', none: null };

export const FRAME_ROOMS: Record<FrameHolds, string> = {
	words: 'cr-ui-frame-holds-words',
	bands: 'cr-ui-frame-holds-bands'
};
