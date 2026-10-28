/**
 * A chip (Chip): what is named, on the tint of whoever named it — a thread
 * or a file named in what is said, in a message to the agent, in its answer,
 * in what it is working on, in the panel's note of a thread it raised; or a
 * chapter of the story, named on a piece's head as another chapter that
 * tells its file. A thread or a file is named in the code's face, in a tag's
 * box (lib/ui/tag.ts), so a chip, a tag and a count in one line stand as
 * tall; a chapter in the page's own face, a step larger, with room round its
 * words, as the story's boards draw a way to one, and is only ever a way to
 * it. Its look is written in styles/ui.css.
 *
 * Pressed, it takes the reader to what it names, by what its caller hands
 * it. One named in a message still being written is taken out of it by its
 * own cross, inside the chip and as tall as its line, in its colour. One
 * that names what the review does not hold is out of reach: named, not a
 * way there, its edge broken. One named on what the reader presses whole to
 * go to what it names — a thread's place on the round's card of it — is
 * that way's mark and no press of its own: a press inside a press is none.
 */

import type { Voice } from './voice';

// The class of each voice, whose words named it, in the library's stylesheet
export const CHIP_VOICES: Record<Voice, string> = { reader: 'cr-ui-chip-reader', agent: 'cr-ui-chip-agent' };

/**
 * What a chip names, which sets its face and its size:
 * - place: a thread's place or a file, in the code's face, in a tag's box
 * - chapter: a chapter of the story, in the page's face, a step larger, with room round its words
 * - part: a part of the page the reader pointed at, by its test ids, drawn as a chapter is
 */
type ChipNames = 'place' | 'chapter' | 'part';

// The class of each in the library's stylesheet
export const CHIP_NAMES: Record<ChipNames, string> = {
	place: 'cr-ui-chip-place',
	chapter: 'cr-ui-chip-chapter',
	part: 'cr-ui-chip-part'
};

/** What a chip naming a part of the page does: is taken out of the feedback by its cross, or only names it. */
export type PartChipReach =
	| {
			/** What its cross does, said to whoever cannot see it and under the pointer. */
			removing: string;
			onRemove: () => void;
	  }
	| { onlyNames: true };

/**
 * What a chip does: takes the reader to what it names; is taken out of a message by its cross; names what is out of
 * reach; or marks what its holder, pressed, takes the reader to.
 */
export type ChipReach =
	| { onclick: () => void }
	| {
			/** What its cross does, said to whoever cannot see it and under the pointer. */
			removing: string;
			onRemove: () => void;
	  }
	| { outOfReach: true }
	| { reachedByItsHolder: true };
