/**
 * A notice (NoticeBar): something the review says of itself — the code
 * moving on under the reader, the diff taken again, what they had not sent
 * brought back, the review over — or of a file, that its lines cannot show.
 * A bar across what it is about, ruled off from what is under it: its mark,
 * its words, and what can be done about it at its far end. Its words stand
 * at one size and in from its edges by one room in every bar, and a bar with
 * nothing to be done about it is as tall as one with a button in it, until
 * its words wrap (styles/ui.css): bars stacked above what is read line up.
 */

/**
 * What a notice is to the reader, said by its ground and by its mark:
 * - reader: what the reader did, or reads the review by — a base picked, the
 *   diff taken again, their unsent comments brought back, a story that shows
 *   part of the change — on their mark's tint, marked in it
 * - warning: what they stand to lose, or must decide about — the code moved
 *   on under them, a draft set aside, a part that could not be drawn, a
 *   review that cannot be reached or ended under them — on the warning's
 *   wash, marked in it
 * - done: the review sent, nothing left to do — on the bars' ground, marked
 *   in the colour of what is done
 * - quiet: a fact of a file that its lines cannot show — that it cannot be
 *   commented on, that its mode changed — no news, so on the bars' ground in
 *   muted words, and unmarked
 */
export type NoticeTone = 'reader' | 'warning' | 'done' | 'quiet';

// The class of each tone in the library's stylesheet
export const NOTICE_TONES: Record<NoticeTone, string> = {
	reader: 'cr-ui-notice-reader',
	warning: 'cr-ui-notice-warning',
	done: 'cr-ui-notice-done',
	quiet: 'cr-ui-notice-quiet'
};
