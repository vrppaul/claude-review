/**
 * Marks laid over stretches of a line of code already highlighted: what
 * changed inside a replaced line, a name the reader asked about. A mark is a
 * span of a class main.css draws, laid into the markup, so the line keeps its
 * highlighting under it.
 */

/** Where a stretch of a line's plain text begins and ends, the end left out. */
export interface TextRange {
	start: number;
	end: number;
}

// What closes a mark, whatever its class
const MARK_CLOSE = '</span>';
// The longest escape the highlighter writes for one character, &quot; and
// its kind, with room to spare: an ampersand further than this from the
// next semicolon is a character of its own
const LONGEST_ESCAPE = 8;

/**
 * Wrap ranges of a line's plain text inside already highlighted markup, in
 * a mark of a class.
 *
 * Offsets refer to the text a reader sees, so tags contribute nothing and an
 * escape such as `&amp;` counts as the one character it stands for. A mark is
 * closed before any tag and reopened after it, so a range crossing a
 * highlight span leaves both properly nested.
 */
export function markRanges(html: string, ranges: TextRange[], markClass: string): string {
	if (ranges.length === 0) return html;

	const writer = new MarkWriter(`<span class="${markClass}">`);
	// The ranges in order: the one the text has reached, or none once it is past the last
	const ahead = ranges.values();
	let range = ahead.next().value;
	let position = 0;
	let plainIndex = 0;

	while (position < html.length) {
		while (range !== undefined && plainIndex >= range.end) range = ahead.next().value;

		if (html.charAt(position) === '<') {
			const close = html.indexOf('>', position);
			const end = close === -1 ? html.length : close + 1;
			writer.tag(html.slice(position, end));
			position = end;
			continue;
		}

		const piece = readCharacter(html, position);
		writer.character(piece, range !== undefined && plainIndex >= range.start);
		position += piece.length;
		plainIndex += 1;
	}

	return writer.finished();
}

/**
 * Writes markup out again with marks around some of its characters.
 *
 * A mark is closed before any tag and opened again after it, so a mark
 * crossing a highlight span leaves both properly nested.
 */
class MarkWriter {
	readonly #markOpen: string;
	#written = '';
	#marking = false;

	/** @param markOpen the tag that opens a mark */
	constructor(markOpen: string) {
		this.#markOpen = markOpen;
	}

	/** A character of the text, inside a mark or out of one. */
	character(piece: string, marked: boolean): void {
		if (marked) this.#open();
		else this.#close();
		this.#written += piece;
	}

	/** A tag of the highlighter's own, which no mark may straddle. */
	tag(markup: string): void {
		this.#close();
		this.#written += markup;
	}

	/** Everything written, with the last mark closed. */
	finished(): string {
		this.#close();
		return this.#written;
	}

	#open(): void {
		if (this.#marking) return;
		this.#written += this.#markOpen;
		this.#marking = true;
	}

	#close(): void {
		if (!this.#marking) return;
		this.#written += MARK_CLOSE;
		this.#marking = false;
	}
}

/** The character of the text at a place in the markup: an escape such as `&amp;` is the one it stands for. */
function readCharacter(html: string, at: number): string {
	const character = html.charAt(at);
	if (character !== '&') return character;
	const semicolon = html.indexOf(';', at);
	const isEntity = semicolon !== -1 && semicolon - at <= LONGEST_ESCAPE;
	return isEntity ? html.slice(at, semicolon + 1) : character;
}
