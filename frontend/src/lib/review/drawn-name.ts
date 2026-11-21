/**
 * A name on a line of a file, found in the line as the page draws it now.
 *
 * A mark over a name and a pane by it stand on a stretch of the line's text.
 * The page draws a line again whenever what it shows changes — a take taken
 * again, a story told again — and a stretch found in the line before is
 * then of text no longer on the page. So a name is kept as where it is, its
 * file, line and column, and whoever draws by it asks each time for the
 * stretch as it is drawn: found again once the text it was found in is gone,
 * and none while the line is not drawn or reads something else there.
 */

import type { NameOnLine } from '$lib/dom/arrived-line.svelte';
import { rangeOfText } from '$lib/dom/caret-text';
import type { FileSections } from '$lib/dom/file-sections';
import { codeOfLine } from '$lib/dom/line-code';
import { stretchOfName } from '$lib/utils/code-words';

export class DrawnName {
	readonly #sections: FileSections;
	readonly #path: string;
	readonly #lineKey: string;
	readonly #name: NameOnLine;
	// The stretch as it was last found, kept while its text is on the page
	#found: Range | null = null;

	/**
	 * @param sections where each line of the review is drawn
	 * @param path the file the name is in
	 * @param lineKey the key the line's place is known by
	 * @param name the name, and the column it starts at
	 */
	constructor(sections: FileSections, path: string, lineKey: string, name: NameOnLine) {
		this.#sections = sections;
		this.#path = path;
		this.#lineKey = lineKey;
		this.#name = name;
	}

	/** The stretch of the code the name is, as its line is drawn now; null while no line drawn reads the name there. */
	readonly stretch = (): Range | null => {
		if (this.#found === null || !this.#reads(this.#found)) this.#found = this.#find();
		return this.#found;
	};

	/** Where the name stands in the window now; null while no line drawn reads it. */
	readonly box = (): DOMRectReadOnly | null => this.stretch()?.getBoundingClientRect() ?? null;

	/** Whether a stretch is text on the page that reads the name. */
	#reads(stretch: Range): boolean {
		return stretch.commonAncestorContainer.isConnected && stretch.toString() === this.#name.name;
	}

	/** Look for the name in its line as drawn now. */
	#find(): Range | null {
		const number = this.#sections.line(this.#path, this.#lineKey);
		const code = number === null ? null : codeOfLine(number);
		if (code === null) return null;
		const { start, end } = stretchOfName(code.textContent, this.#name.column, this.#name.name);
		const stretch = rangeOfText(code, start, end);
		return this.#reads(stretch) ? stretch : null;
	}
}
