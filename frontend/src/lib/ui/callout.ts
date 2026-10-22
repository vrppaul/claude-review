/**
 * A callout (Callout): what a part of the page says of itself before what it
 * heads, which the reader should know before reading on — that the agent
 * which told a story did not make the change, but read it out of the code
 * and its commits. On its tone's tint, rounded, with no edge; its mark at its
 * start and its first words in its tone's colour, its other words in ink. Its
 * look is written in styles/ui.css.
 */

import type { IconName, IconTone } from './icons';

/**
 * Whose word it is, by its colour and its mark:
 * - agent: what the agent says of how it told the story, by the agent's own mark
 */
export type CalloutTone = 'agent';

/** How each tone is drawn: its class in the library's stylesheet, and the mark at its start in its colour. */
interface CalloutLook {
	look: string;
	icon: IconName;
	iconTone: IconTone;
}

export const CALLOUT_LOOKS: Record<CalloutTone, CalloutLook> = {
	agent: { look: 'cr-ui-callout-agent', icon: 'story', iconTone: 'agent' }
};
