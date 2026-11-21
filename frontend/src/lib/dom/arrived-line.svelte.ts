/**
 * The line the page took the reader to, lit until the keyboard leaves it.
 *
 * A page that jumped leaves the reader working out where they landed, and
 * the keyboard's ring round a line's number is small to find. So the line
 * the page put the keyboard on stands lit while the keyboard stays there,
 * and goes out the moment the reader moves on: a line they step to
 * themselves was not arrived at. Where they were taken to a name on the
 * line, the name stands marked on it as long.
 */

/** A name on a line: the column it starts at, in characters as the review counts them, and the name itself. */
export interface NameOnLine {
	column: number;
	name: string;
}

/** A line arrived at in a section: the key its place is known by, and the name on it gone to, if one was. */
export interface LineArrivedAt {
	line: string;
	name: NameOnLine | null;
}

/** A line arrived at, and the section it is drawn in. */
interface ArrivedInSection extends LineArrivedAt {
	section: string;
}

export class ArrivedLine {
	#at = $state.raw<ArrivedInSection | null>(null);
	// What hears the keyboard leave the line arrived at
	#leaving = new AbortController();

	/** The line arrived at in a section; null in any other section, and once the keyboard left it. */
	lineIn(section: string): LineArrivedAt | null {
		const at = this.#at;
		return at !== null && at.section === section ? at : null;
	}

	/**
	 * The page put the keyboard on a line's number in a section, taking the reader to a name on it or to the line
	 * alone: the line stands lit, and the name marked, until the keyboard leaves it.
	 */
	light(section: string, arrived: LineArrivedAt, number: HTMLElement): void {
		this.#leaving.abort();
		const leaving = new AbortController();
		this.#leaving = leaving;
		this.#at = { section, ...arrived };
		// The number may lose the keyboard by going with its view, in the middle of the page drawing what replaces
		// it, when nothing the page draws from may change: the light goes out once that is done
		number.addEventListener('blur', () => queueMicrotask(() => this.#putOutOnceLeft(number, leaving)), {
			signal: leaving.signal
		});
	}

	/** Put the light out, unless the line was arrived at anew since, or the keyboard is on its number still. */
	#putOutOnceLeft(number: HTMLElement, leaving: AbortController): void {
		// A window the reader leaves blurs what holds the keyboard, which holds it still when they are back
		if (leaving.signal.aborted || document.activeElement === number) return;
		leaving.abort();
		this.#at = null;
	}
}
