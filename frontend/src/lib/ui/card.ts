/**
 * A card (Card): what it holds boxed apart from what stands round it — a
 * thread, a comment being written as the card it becomes, the agent's
 * answer in the panel and its work while it does it, the facts of a story
 * on its way. Every one on a raised surface, edged by a line in its tone's
 * colour, at the box's corner, with one room round what it holds
 * (styles/ui.css). How what it holds is laid out inside is its holder's.
 *
 * A card that hangs under what it is about is lifted off it, and points up
 * at it with a tail where it hangs: the card places its tail itself, from
 * where it is told it hangs, and nothing outside the library reaches into it.
 */

/**
 * Whose the card is, or where what it holds stands, said by its edge:
 * - quiet: a line between surfaces, saying nothing more; a thread that went
 *   out with a round, quieter than one still in the reader's hands
 * - reader: a thread in the reader's hands, a comment they are writing
 * - agent: a thread the agent raised
 * - stale: a thread whose lines are gone
 */
export type CardTone = 'quiet' | 'reader' | 'agent' | 'stale';

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
	stale: 'cr-ui-card-stale'
};

export const CARD_HANGINGS: Record<CardHanging, string> = {
	line: 'cr-ui-card-hanging cr-ui-card-tailed cr-ui-card-under-a-line',
	block: 'cr-ui-card-hanging cr-ui-card-tailed cr-ui-card-under-a-block',
	head: 'cr-ui-card-hanging'
};
