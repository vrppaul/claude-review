/**
 * A tag (Tag): a word or two said beside a heading or a name — what a
 * thread asks for, that it is outdated, resolved or the agent's; the round a
 * story was told in, where else a step's file is told; a measure said
 * quietly — in a line round them of the colour they are said in. Its words
 * are shown as they are written: a tag holds a measure too, and "1M"
 * lowercased would read as "1m".
 *
 * A count (Count) stands in the same box, so a tag and a count in one line
 * stand as tall, whatever line that is: small words at a leading of their
 * own, at a field's corner, as a button and a chip at that size have it,
 * never a pill. Both are written in styles/ui.css.
 */

/**
 * Whose the words are, or what they say, by their colour:
 * - quiet: something settled or stepping back — outdated, resolved — or a
 *   measure said quietly
 * - reader: asked by the reader
 * - agent: the agent's — what it asks, that it raised a thread, the round
 *   its story was told in, where else it tells a file
 * - warning: what the reader is warned of — a story whose code moved on,
 *   threads the view on screen does not show
 * - blocking: what has to be dealt with before going on, on the warning's
 *   own fill and in bold
 */
export type TagTone = 'quiet' | 'reader' | 'agent' | 'warning' | 'blocking';

// The class of each tone in the library's stylesheet
export const TAG_TONES: Record<TagTone, string> = {
	quiet: 'cr-ui-tag-quiet',
	reader: 'cr-ui-tag-reader',
	agent: 'cr-ui-tag-agent',
	warning: 'cr-ui-tag-warning',
	blocking: 'cr-ui-tag-blocking'
};
