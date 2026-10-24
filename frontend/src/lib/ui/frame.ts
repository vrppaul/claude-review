/**
 * Where words stand apart from what is round them, and the band that lights
 * a block of them the reader may ask about.
 *
 * Code a story tells stands in a frame of its own (CodeFrame), edged as a
 * pane and rounded; what heads the code, the step's reason, is the frame's
 * top line (CodeFrameHead), after the agent's avatar, a rule under it, and
 * the file's bar and lines follow inside; where no code is drawn, a row as
 * tall as a file's bar says what stands in its place (CodeFrameRow).
 *
 * A band (Band) is a block of words the reader may ask about, lit while it
 * is pointed at or holds the keyboard, offering its act; what hangs under it
 * hangs from where its band ends. Where its words stand sets how far it
 * reaches past them and where its offer stands:
 *
 * - In no frame, as a chapter's why: its band stands on the edges of the
 *   part it stands in, as a card does, its words in from them as far as a
 *   card stands its words in, and reaches above and below them as far as a
 *   band reaches, taking that room, so it stands that far from what is round
 *   it; it offers its act over its top right edge. What hangs under it is as
 *   wide as its band.
 * - On a card of its own (Card, washed): one line of what a story says in
 *   short, on the wash of whose it is. Its band fills the card, lit to the
 *   card's edge, and offers its act inside the card's top right corner.
 *   What hangs under it is as wide as the card.
 * - As an item of a list on a card of lists (ListsCardRow), on no frame of
 *   its own: its light a pill round its words, reaching a step and a half
 *   past them above and below and two to either side and taking none of
 *   that room; its offer in a column of its own beside the words, kept while
 *   unseen, so no word moves as it shows. What hangs under it is as wide as
 *   that light.
 * - As the top line of a frame of code: its band is that line
 *   (CodeFrameHead), lit across the frame, its offer at the line's end. What
 *   hangs under it hangs in the frame, over the code.
 *
 * Blocks one under another (Bands) stand as close as cards in a stack,
 * whichever they are. The frames, the card, the band and their stack are
 * drawn together here and in the library's stylesheet, so nothing outside
 * the library lays out round them.
 */

import type { WashedTone } from './card';

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

/** What heads a piece of code, the top line of its frame (CodeFrame). */
interface HeadingCodeLook {
	shape: 'heading-code';
}

/** Where a band's words stand: for whoever hands it on, as a block of a story hands on where its words stand. */
export type FrameLook = UnframedLook | CardLook | ListedLook | HeadingCodeLook;

// The class of a band (Band) by where its words stand, in the library's stylesheet
export const BANDS_BY_FRAME: Record<FrameLook['shape'], string> = {
	unframed: 'cr-ui-band-unframed',
	card: 'cr-ui-band-on-a-card',
	listed: 'cr-ui-band-listed',
	'heading-code': 'cr-ui-band-heading-code'
};
