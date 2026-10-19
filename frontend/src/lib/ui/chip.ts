/**
 * A chip (Chip): a thread or a file named in what is said — in a message to
 * the agent, in its answer, in what it is working on, in the panel's note of
 * a thread it raised — in the code's face, on the tint of whoever named it,
 * in a tag's box (lib/ui/tag.ts), so a chip, a tag and a count in one line
 * stand as tall. Its look is written in styles/ui.css.
 *
 * Pressed, it takes the reader to what it names, by what its caller hands
 * it. One named in a message still being written is taken out of it by its
 * own cross, inside the chip and as tall as its line, in its colour. One
 * that names what the review does not hold is out of reach: named, not a
 * way there, its edge broken.
 */

/** Whose words named it, by their colour: the reader's, or the agent's. */
export type ChipVoice = 'reader' | 'agent';

// The class of each voice in the library's stylesheet
export const CHIP_VOICES: Record<ChipVoice, string> = { reader: 'cr-ui-chip-reader', agent: 'cr-ui-chip-agent' };

/** What a chip does: takes the reader to what it names; is taken out of a message by its cross; or names what is out of reach. */
export type ChipReach =
	| { onclick: () => void }
	| {
			/** What its cross does, said to whoever cannot see it and under the pointer. */
			removing: string;
			onRemove: () => void;
	  }
	| { outOfReach: true };
