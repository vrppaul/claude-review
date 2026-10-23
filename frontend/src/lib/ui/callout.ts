/**
 * A callout (Callout): what the reader should know before reading on or
 * acting — that the agent which told a story did not make the change, but
 * read it out of the code and its commits; that a round changed a chapter's
 * code after the chapter was told; what a story will cost, before one is
 * asked for. On its tone's tint, rounded, with no edge; its mark at its start
 * and its first words in its tone's colour, its other words in ink. What the
 * agent is doing about what it says, while it does, stands on a line of its
 * own under its words, in the agent's colour, after dots that breathe. Its
 * look is written in styles/ui.css.
 */

import type { IconName, IconTone } from './icons';

/**
 * Whose word it is, or what it warns of, by its colour and its mark:
 * - agent: what the agent says of how it told the story, by the agent's own mark
 * - warning: what to weigh before going on — what changed under what a part says since it was said, what a story
 *   costs — by the mark of what to look at
 */
export type CalloutTone = 'agent' | 'warning';

/** How each tone is drawn: its class in the library's stylesheet, and the mark at its start in its colour. */
interface CalloutLook {
	look: string;
	icon: IconName;
	iconTone: IconTone;
}

export const CALLOUT_LOOKS: Record<CalloutTone, CalloutLook> = {
	agent: { look: 'cr-ui-callout-agent', icon: 'story', iconTone: 'agent' },
	warning: { look: 'cr-ui-callout-warning', icon: 'warning', iconTone: 'warning' }
};
