/**
 * A list of keys (KeyList): each row the keys of one thing done, and what it
 * does. Whoever lists keys — the help, from the review's keymap — hands it
 * rows of this shape, the keys already named as the reader reads them.
 */

/** A row of the list: one key, or two that do opposite things in the order `does` names them; and what they do. */
export interface ListedKeys {
	keys: readonly string[];
	does: string;
}
