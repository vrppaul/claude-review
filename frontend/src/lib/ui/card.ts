/**
 * A card (Card): what it holds boxed apart from what stands round it — a
 * thread, a comment being written as the card it becomes, the facts of a
 * story on its way. Every one on a card's ground, edged by a line in its
 * tone's colour, at the box's corner, with one room round what it holds
 * (styles/ui.css). How what it holds is laid out inside is its holder's.
 * Code set apart to read or copy (CodeBox) stands on a quiet one.
 *
 * A card that hangs under what it is about is lifted off it, and points up
 * at it with a tail where it hangs: the card places its tail itself, from
 * where it is told it hangs, and nothing outside the library reaches into it.
 *
 * A card headed by a bar (CardBar) is laid out by its parts: the bar, what
 * it holds under the bar, and its foot, each keeping the card's room either
 * side, so all three start and end on one edge. Folded, the bar stands alone.
 * The bar's ground is the tone's wash over the card's, and so is its tail's.
 *
 * A washed card lays its tone's wash over the whole of it, in place of the
 * card's ground: one line of what a story says in short, on a card of its
 * own in the colour of whose it is; what to look at a step stronger, at the
 * tint, as the line the reader should read first.
 */

/**
 * Whose the card is, or where what it holds stands, said by its edge and its bar:
 * - quiet: a line between surfaces, saying nothing more; a thread that went
 *   out with a round, quieter than one still in the reader's hands
 * - reader: a thread in the reader's hands, a comment they are writing
 * - agent: a thread the agent raised
 * - stale: a thread whose lines are gone
 * - done: a thread settled, its bar on the tint of what is done
 * - warning: what to look at, where a story says to doubt its change
 */
export type CardTone = 'quiet' | 'reader' | 'agent' | 'stale' | 'done' | 'warning';

/** The tones a card is washed in: the reader's, the agent's, and what to look at. */
export type WashedTone = 'reader' | 'agent' | 'warning';

/**
 * Where a card hangs, lifted off what it is about:
 * - line: under a line of code, pointing up at it
 * - block: under a block of a story's words, pointing up at its heading
 * - head: at the head of a file, the diff or a story it lost its place in,
 *   where nothing drawn above it is what it is about, so pointing at nothing
 */
export type CardHanging = 'line' | 'block' | 'head';

// The class of each tone, and of each place a card hangs, in the library's stylesheet
export const CARD_TONES: Record<CardTone, string> = {
	quiet: 'cr-ui-card-quiet',
	reader: 'cr-ui-card-reader',
	agent: 'cr-ui-card-agent',
	stale: 'cr-ui-card-stale',
	done: 'cr-ui-card-done',
	warning: 'cr-ui-card-warning'
};

export const CARD_HANGINGS: Record<CardHanging, string> = {
	line: 'cr-ui-card-hanging cr-ui-card-tailed cr-ui-card-under-a-line',
	block: 'cr-ui-card-hanging cr-ui-card-tailed cr-ui-card-under-a-block',
	head: 'cr-ui-card-hanging'
};
