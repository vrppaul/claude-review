/**
 * A twin chip (TwinChip): how much a part of the story holds, counted, a
 * half to each count — a chapter's files and its steps — side by side on
 * the agent's chip, a half step apart and rounded as one. It only says, so
 * it has no states and looks like no control, unlike a chip that names a
 * way (Chip, lib/ui/chip.ts): no edge, its words of normal weight. Where a
 * count has nothing to say it has no half, as a chapter none of whose code
 * is found any more counts its steps alone. Its look is written in
 * styles/ui.css.
 */

import type { IconName } from './icons';

/** One count of a twin chip: its mark, and its words, the count and what it counts. */
export interface TwinHalf {
	icon: IconName;
	words: string;
}
