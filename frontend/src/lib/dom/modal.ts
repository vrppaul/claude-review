/**
 * A modal dialog open over the page, as whatever lies under it must take
 * it: a layer above every pane and note. A key pressed or a press made in
 * the modal is the modal's, and nothing under it answers either.
 */

/**
 * Whether something is in a modal dialog open over the page. A modal is a
 * layer above every pane: one opened from inside a pane — the help, by ? —
 * leaves the pane open under it, takes the keyboard, the presses and
 * Escape while it is open, and gives the keyboard back into the pane as it
 * closes.
 */
export function inModalAbove(target: EventTarget | null): boolean {
	return target instanceof Element && target.closest('dialog[open]') !== null;
}
