/**
 * The line the page took the reader to, lit until the keyboard leaves it.
 *
 * A page that jumped leaves the reader working out where they landed, and
 * the keyboard's ring round a line's number is small to find. So the line
 * the page put the keyboard on stands lit while the keyboard stays there,
 * and goes out the moment the reader moves on: a line they step to
 * themselves was not arrived at.
 */

/** A line arrived at: the section it is drawn in, and the key its place is known by. */
interface LineArrivedAt {
	section: string;
	line: string;
}

export class ArrivedLine {
	#at = $state.raw<LineArrivedAt | null>(null);
	// What hears the keyboard leave the line arrived at
	#leaving = new AbortController();

	/** The line arrived at in a section, by the key its place is known by; null in any other section, and once the keyboard left it. */
	lineIn(section: string): string | null {
		const at = this.#at;
		return at !== null && at.section === section ? at.line : null;
	}

	/** The page put the keyboard on a line's number in a section: the line stands lit until the keyboard leaves it. */
	light(section: string, line: string, number: HTMLElement): void {
		this.#leaving.abort();
		this.#leaving = new AbortController();
		this.#at = { section, line };
		number.addEventListener('blur', () => this.#putOutOnceLeft(number), { signal: this.#leaving.signal });
	}

	#putOutOnceLeft(number: HTMLElement): void {
		// A window the reader leaves blurs what holds the keyboard, which holds it still when they are back
		if (document.activeElement === number) return;
		this.#leaving.abort();
		this.#at = null;
	}
}
