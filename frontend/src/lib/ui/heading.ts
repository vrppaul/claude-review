/**
 * What a heading heads, which sets its size and face, and the tone it is
 * said in: each a class of the library's stylesheet (styles/ui.css), where
 * its look is written from the scale's tokens.
 *
 * A heading of the page is drawn by `Heading`, and nothing outside the
 * library draws one: a heading the page needs is a kind or a tone here, with
 * the reason a reader needs it.
 */

/**
 * - story: the story's own title, or what stands in its place while it is
 *   written, at the largest of the scale's sizes.
 * - part: a part of the story, a chapter or what the story leaves out: its
 *   number, where it has one, beside its title, which wraps beside it.
 * - pane: a pane, a column beside what is read, the question a pane asks, a
 *   step of the tour, a list on a card of lists — one size for all of them.
 * - list: a small head over what stands under it inside one of those — a
 *   line of the overview, a chapter's warning — at the size of its words.
 * - piece: a piece of code, by its file's name or by a step's number, in the
 *   code's face, a name broken anywhere rather than run past its column.
 */
export type HeadingKind = 'story' | 'part' | 'pane' | 'list' | 'piece';

/**
 * The tone it is said in, where it is not the page's own words: the reader's,
 * the agent's, a warning, quieter, or stepping back as what is finished with
 * does.
 */
export type HeadingTone = 'reader' | 'agent' | 'warning' | 'quiet' | 'faint';

/**
 * What it is to whoever goes through the page by its headings: a heading at
 * a level, or plain words where something else heads the part it stands in.
 */
export type HeadingTag = 'h1' | 'h2' | 'h3' | 'p';

export const HEADING_KINDS: Record<HeadingKind, string> = {
	story: 'cr-ui-heading-story',
	part: 'cr-ui-heading-part',
	pane: 'cr-ui-heading-pane',
	list: 'cr-ui-heading-list',
	piece: 'cr-ui-heading-piece'
};

export const HEADING_TONES: Record<HeadingTone, string> = {
	reader: 'cr-ui-heading-reader',
	agent: 'cr-ui-heading-agent',
	warning: 'cr-ui-heading-warning',
	quiet: 'cr-ui-heading-quiet',
	faint: 'cr-ui-heading-faint'
};
