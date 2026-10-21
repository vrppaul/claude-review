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
 * The frame, the band and their stack are drawn together here and in the
 * library's stylesheet, so nothing outside the library lays out round them.
 */

/**
 * Whose or what the framed words are, and the ground the tone lays:
 * - agent: what the agent says in a story; on its wash
 * - warning: what the review warns about, where to doubt it, what it costs;
 *   on its wash
 */
export type FrameTone = 'agent' | 'warning';

/** Whether the frame lays its tone's ground under the words, or stands them on what is under it. */
export type FrameGround = 'tint' | 'none';

/** How a frame is drawn: for whoever hands one on, as a block of a story hands on the frame its words stand in. */
export interface FrameLook {
	tone: FrameTone;
	ground: FrameGround;
	/** Its edge broken: words read out of the code, not said by whoever made it. */
	dashed?: boolean | undefined;
}

// The class of each tone, and of a ground, in the library's stylesheet
export const FRAME_TONES: Record<FrameTone, string> = {
	agent: 'cr-ui-frame-agent',
	warning: 'cr-ui-frame-warning'
};

export const FRAME_GROUNDS: Record<FrameGround, string | null> = { tint: 'cr-ui-frame-tinted', none: null };
