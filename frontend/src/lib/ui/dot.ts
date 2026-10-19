/**
 * A dot (Dot): a mark for the eye beside the words that say what it marks
 * to everyone — an answer not read yet, how the agent stands with the
 * review, what the tour waits for, a file changed since the reader's round
 * — round, at one size, in its tone's colour. One that breathes says
 * what it marks is on its way: a turn of the agent's, a branch of its work;
 * dots side by side breathe in turn. Never said to a screen reader: the
 * words beside it say it. Its look is written in styles/ui.css.
 */

/**
 * What a dot says by its colour:
 * - unread: what the agent brought that the reader has not read
 * - agent: the agent at work
 * - done: something ready — an agent listening
 * - absent: nobody there, as far as the page can tell
 * - quiet: something on its way, saying no more than that
 * - reader: the reader's — what the tour waits for them to do, a file
 *   changed since the round they sent
 * - inherited: in the colour of what it stands in, which says what it marks:
 *   the overview's node in a story's contents, faint, or the reader's while
 *   it is the part being read
 */
export type DotTone = 'unread' | 'agent' | 'done' | 'absent' | 'quiet' | 'reader' | 'inherited';

// The class of each tone in the library's stylesheet
export const DOT_TONES: Record<DotTone, string> = {
	unread: 'cr-ui-dot-unread',
	agent: 'cr-ui-dot-agent',
	done: 'cr-ui-dot-done',
	absent: 'cr-ui-dot-absent',
	quiet: 'cr-ui-dot-quiet',
	reader: 'cr-ui-dot-reader',
	inherited: 'cr-ui-dot-inherited'
};
