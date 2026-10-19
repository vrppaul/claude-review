/**
 * A field the reader writes in (Field), a filter they narrow a list with
 * (Filter), and the field a reply is begun in, a press until it is begun
 * (FieldButton): each on the ground of whatever it stands in, so only its
 * edge, in the colour of whose words go in it, says it is the reader's to
 * fill. Their look is written in styles/ui.css.
 */

/**
 * What a field holds, which sets how tall it stands before anything is
 * written in it:
 * - comment: a comment on what is read, or a reply in a thread; it grows
 *   with what is written, as a suggestion fills it with lines at once, up to
 *   the tallest a field stands, and scrolls from there
 * - message: what is sent to the agent from a pane's foot, the summary of a
 *   review or a message in the panel; shorter, so the pane keeps room for
 *   what it shows above it
 */
export type FieldHolds = 'comment' | 'message';

/** Whose thread it is written in, by the colour of its edge: the reader's, or one the agent raised. */
export type FieldVoice = 'reader' | 'agent';

/** How a field holding each is drawn: its class in the library's stylesheet, and whether it grows with its words. */
export const FIELD_HOLDS: Record<FieldHolds, { drawnAs: string; grows: boolean }> = {
	comment: { drawnAs: 'cr-ui-field-comment', grows: true },
	message: { drawnAs: 'cr-ui-field-message', grows: false }
};

// The class of each voice in the library's stylesheet; the reader's edge is every field's own
export const FIELD_VOICES: Record<FieldVoice, string | null> = { reader: null, agent: 'cr-ui-field-agent' };
