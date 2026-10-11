import { commonTokens, type Token } from '$lib/utils/common-tokens';
import type { HighlightedLine } from '$lib/utils/highlight';
import { type Run, runsOf } from '$lib/utils/replacements';

/** Beyond this, the line is long enough that the table costs more than the
 * marking is worth, and a line that long is rarely read word by word. */
const MAX_TOKENS = 400;

/** Above this share of a line marked, the marking is confetti and says less
 * than the row colour already does. */
const MAX_MARKED_SHARE = 0.5;

/** Two changes this close together read as one edit, and the punctuation or
 * space between them does not deserve a gap in the marking. */
const JOIN_WITHIN = 2;

/** Where a stretch of a line's plain text begins and ends, the end left out. */
export interface TextRange {
	start: number;
	end: number;
}

/** What changed in a replaced line, and in the line that replaced it. */
interface WordRanges {
	removed: TextRange[];
	added: TextRange[];
}

// How a changed stretch is marked inside highlighted markup
const MARK_OPEN = '<span class="cr-word">';
const MARK_CLOSE = '</span>';
// The longest escape the highlighter writes for one character, &quot; and
// its kind, with room to spare: an ampersand further than this from the
// next semicolon is a character of its own
const LONGEST_ESCAPE = 8;

/**
 * Which parts of a replaced line actually changed.
 *
 * A row coloured end to end says a line changed but not where, and most
 * replacements touch a word or two. Comparing by word rather than character
 * keeps the marks on things a reader recognises — an identifier, a number, an
 * argument — instead of scattering them mid-token.
 */
export function wordRanges(removedText: string, addedText: string): WordRanges {
	const before = tokenize(removedText);
	const after = tokenize(addedText);
	const none: WordRanges = { removed: [], added: [] };

	if (before.length > MAX_TOKENS || after.length > MAX_TOKENS) return none;

	const common = commonTokens(before, after);
	if (common.before.every((token) => token.kept) && common.after.every((token) => token.kept)) {
		return none;
	}

	const removed = join(rangesOfChanged(common.before));
	const added = join(rangesOfChanged(common.after));

	const marked = covered(removed) + covered(added);
	const total = removedText.length + addedText.length;
	if (total === 0 || marked / total > MAX_MARKED_SHARE) return none;

	return { removed, added };
}

/**
 * Wrap ranges of a line's plain text inside already highlighted markup.
 *
 * Offsets refer to the text a reader sees, so tags contribute nothing and an
 * escape such as `&amp;` counts as the one character it stands for. A mark is
 * closed before any tag and reopened after it, so a range crossing a
 * highlight span leaves both properly nested.
 */
export function markRanges(html: string, ranges: TextRange[]): string {
	if (ranges.length === 0) return html;

	const writer = new MarkWriter();
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
	#written = '';
	#marking = false;

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
		this.#written += MARK_OPEN;
		this.#marking = true;
	}

	#close(): void {
		if (!this.#marking) return;
		this.#written += MARK_CLOSE;
		this.#marking = false;
	}
}

/**
 * Mark what changed inside each replaced line of a hunk.
 *
 * A removed line is marked against the added line that replaced it, as the
 * hunk's replacements pair them. A line with no counterpart is left alone,
 * since nothing was replaced.
 */
export function withWordMarks<Line extends HighlightedLine>(lines: readonly Line[]): Line[] {
	return runsOf(lines).flatMap(markedRun);
}

function markedRun<Line extends HighlightedLine>(run: Run<Line>): Line[] {
	if (run.kind === 'kept') return [run.line];
	const { removed, added } = run;
	const ranges = removed.map((line, offset) => rangesAgainst(line, added.at(offset)));
	return [
		...removed.map((line, offset) => withMarks(line, ranges.at(offset)?.removed)),
		...added.map((line, offset) => withMarks(line, ranges.at(offset)?.added))
	];
}

/** What changed between a removed line and the line that replaced it; null when nothing replaced it. */
function rangesAgainst(removed: HighlightedLine, added: HighlightedLine | undefined): WordRanges | null {
	return added ? wordRanges(removed.line.content, added.line.content) : null;
}

/** A line with its changed stretches marked, or as it was when it has none to mark. */
function withMarks<Line extends HighlightedLine>(line: Line, ranges: TextRange[] | undefined): Line {
	return ranges ? { ...line, markup: markRanges(line.markup, ranges) } : line;
}

/** Split into words, runs of whitespace, and single punctuation marks. */
function tokenize(text: string): string[] {
	return text.match(/\s+|[A-Za-z0-9_]+|[^\sA-Za-z0-9_]/g) ?? [];
}

/** The character of the text at a place in the markup: an escape such as `&amp;` is the one it stands for. */
function readCharacter(html: string, at: number): string {
	const character = html.charAt(at);
	if (character !== '&') return character;
	const semicolon = html.indexOf(';', at);
	const isEntity = semicolon !== -1 && semicolon - at <= LONGEST_ESCAPE;
	return isEntity ? html.slice(at, semicolon + 1) : character;
}

/** Merge ranges with only a character or two between them. */
function join(ranges: TextRange[]): TextRange[] {
	const merged: TextRange[] = [];
	for (const range of ranges) {
		const last = merged.at(-1);
		if (last !== undefined && range.start - last.end <= JOIN_WITHIN) last.end = range.end;
		else merged.push({ ...range });
	}
	return merged;
}

function covered(ranges: TextRange[]): number {
	return ranges.reduce((total, range) => total + (range.end - range.start), 0);
}

/** Character ranges covering the tokens that are not shared. */
function rangesOfChanged(tokens: Token[]): TextRange[] {
	const ranges: TextRange[] = [];
	let offset = 0;
	let runStart: number | null = null;

	for (const token of tokens) {
		if (!token.kept) {
			if (runStart === null) runStart = offset;
		} else if (runStart !== null) {
			ranges.push({ start: runStart, end: offset });
			runStart = null;
		}
		offset += token.text.length;
	}

	if (runStart !== null) ranges.push({ start: runStart, end: offset });
	return ranges;
}
