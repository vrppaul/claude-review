/**
 * The code of a line, found from the line's number: what marks a name on a
 * line needs, where only the number is known by the line's place.
 */

// What a line's code is known by in its row, after its number (RawView, SplitView)
export const LINE_CODE_ROLE = 'line-code';

/**
 * The code of the line a number is of: the first code that follows the
 * number in its row, looked for among what follows the number and, outward,
 * what holds it. A row reads a line's number before its code, in one layout
 * and in two.
 */
export function codeOfLine(number: HTMLElement): HTMLElement | null {
	for (let holder: Element | null = number; holder !== null; holder = holder.parentElement) {
		for (let next = holder.nextElementSibling; next !== null; next = next.nextElementSibling) {
			if (next instanceof HTMLElement && next.dataset.role === LINE_CODE_ROLE) return next;
		}
	}
	return null;
}
