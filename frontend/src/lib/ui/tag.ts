/**
 * A tag (Tag): a word or two said beside a heading or a name — what a
 * thread asks for, that it is outdated, resolved or the agent's; a measure
 * said quietly — on the chip of the colour they are said in, with no edge.
 * Its words are shown as they are written: a tag holds a measure too, and
 * "1M" lowercased would read as "1m".
 *
 * A count (Count) and a chip naming a place (Chip, lib/ui/chip.ts) stand in the same box,
 * so marks in one line stand as tall, whatever line that is: small words at
 * a leading of their own, at a field's corner, as a button at that size has
 * it, never a pill. All three are written in styles/ui.css.
 */

/**
 * Whose the words are, or what they say, by their colour:
 * - quiet: something settled, a thread resolved, or a measure said quietly,
 *   as the release something is new in
 * - reader: asked by the reader
 * - agent: the agent's — what it asks, that it raised a thread
 * - warning: what the reader is warned of or must deal with — a blocker, a
 *   thread out of date, threads the view on screen does not show
 */
export type TagTone = 'quiet' | 'reader' | 'agent' | 'warning';

// The class of each tone in the library's stylesheet
export const TAG_TONES: Record<TagTone, string> = {
	quiet: 'cr-ui-tag-quiet',
	reader: 'cr-ui-tag-reader',
	agent: 'cr-ui-tag-agent',
	warning: 'cr-ui-tag-warning'
};
