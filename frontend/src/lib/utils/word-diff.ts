import type { DiffLine } from '$lib/types';

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
export function wordRanges(removedText: string, addedText: string): { removed: TextRange[]; added: TextRange[] } {
	const before = tokenize(removedText);
	const after = tokenize(addedText);
	const none = { removed: [], added: [] };

	if (before.length > MAX_TOKENS || after.length > MAX_TOKENS) return none;

	const common = longestCommonSubsequence(before, after);
	if (common.beforeKept.every(Boolean) && common.afterKept.every(Boolean)) {
		return none;
	}

	const removed = join(rangesOfChanged(before, common.beforeKept));
	const added = join(rangesOfChanged(after, common.afterKept));

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
	let position = 0;
	let plainIndex = 0;
	let rangeIndex = 0;

	while (position < html.length) {
		while (rangeIndex < ranges.length && plainIndex >= ranges[rangeIndex].end) {
			rangeIndex += 1;
		}

		if (html[position] === '<') {
			const close = html.indexOf('>', position);
			const end = close === -1 ? html.length : close + 1;
			writer.tag(html.slice(position, end));
			position = end;
			continue;
		}

		const piece = readCharacter(html, position);
		const range = ranges[rangeIndex];
		writer.character(piece, range !== undefined && plainIndex >= range.start && plainIndex < range.end);
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
 * Removals and the additions that follow them are read as one replacement,
 * paired in order: the first removed line against the first added one. A line
 * with no counterpart is left alone, since nothing was replaced.
 */
export function applyWordMarks(lines: DiffLine[], html: string[]): string[] {
	const result = [...html];

	let index = 0;
	while (index < lines.length) {
		if (lines[index].kind !== 'delete') {
			index += 1;
			continue;
		}

		const removalStart = index;
		while (index < lines.length && lines[index].kind === 'delete') index += 1;
		const additionStart = index;
		while (index < lines.length && lines[index].kind === 'add') index += 1;

		const removals = additionStart - removalStart;
		const additions = index - additionStart;
		for (let offset = 0; offset < Math.min(removals, additions); offset += 1) {
			const removedAt = removalStart + offset;
			const addedAt = additionStart + offset;
			const { removed, added } = wordRanges(lines[removedAt].content, lines[addedAt].content);
			result[removedAt] = markRanges(result[removedAt], removed);
			result[addedAt] = markRanges(result[addedAt], added);
		}
	}

	return result;
}

/** Split into words, runs of whitespace, and single punctuation marks. */
function tokenize(text: string): string[] {
	return text.match(/\s+|[A-Za-z0-9_]+|[^\sA-Za-z0-9_]/g) ?? [];
}

function readCharacter(html: string, at: number): string {
	if (html[at] !== '&') return html[at];
	const semicolon = html.indexOf(';', at);
	const isEntity = semicolon !== -1 && semicolon - at <= LONGEST_ESCAPE;
	return isEntity ? html.slice(at, semicolon + 1) : html[at];
}

/** Merge ranges with only a character or two between them. */
function join(ranges: TextRange[]): TextRange[] {
	// One range, or none, has nothing to be merged with
	if (ranges.length <= 1) return ranges;

	const merged: TextRange[] = [{ ...ranges[0] }];
	for (const range of ranges.slice(1)) {
		const last = merged[merged.length - 1];
		if (range.start - last.end <= JOIN_WITHIN) last.end = range.end;
		else merged.push({ ...range });
	}
	return merged;
}

function covered(ranges: TextRange[]): number {
	return ranges.reduce((total, range) => total + (range.end - range.start), 0);
}

function longestCommonSubsequence(before: string[], after: string[]): { beforeKept: boolean[]; afterKept: boolean[] } {
	const rows = before.length;
	const columns = after.length;
	const table: number[][] = Array.from({ length: rows + 1 }, () => new Array<number>(columns + 1).fill(0));

	for (let beforeIndex = rows - 1; beforeIndex >= 0; beforeIndex -= 1) {
		for (let afterIndex = columns - 1; afterIndex >= 0; afterIndex -= 1) {
			table[beforeIndex][afterIndex] =
				before[beforeIndex] === after[afterIndex]
					? table[beforeIndex + 1][afterIndex + 1] + 1
					: Math.max(table[beforeIndex + 1][afterIndex], table[beforeIndex][afterIndex + 1]);
		}
	}

	const beforeKept = new Array<boolean>(rows).fill(false);
	const afterKept = new Array<boolean>(columns).fill(false);
	let beforeIndex = 0;
	let afterIndex = 0;
	while (beforeIndex < rows && afterIndex < columns) {
		if (before[beforeIndex] === after[afterIndex]) {
			beforeKept[beforeIndex] = true;
			afterKept[afterIndex] = true;
			beforeIndex += 1;
			afterIndex += 1;
		} else if (table[beforeIndex + 1][afterIndex] >= table[beforeIndex][afterIndex + 1]) {
			beforeIndex += 1;
		} else {
			afterIndex += 1;
		}
	}

	return { beforeKept, afterKept };
}

/** Character ranges covering the tokens that are not shared. */
function rangesOfChanged(tokens: string[], kept: boolean[]): TextRange[] {
	const ranges: TextRange[] = [];
	let offset = 0;
	let runStart: number | null = null;

	tokens.forEach((token, index) => {
		if (!kept[index]) {
			if (runStart === null) runStart = offset;
		} else if (runStart !== null) {
			ranges.push({ start: runStart, end: offset });
			runStart = null;
		}
		offset += token.length;
	});

	if (runStart !== null) ranges.push({ start: runStart, end: offset });
	return ranges;
}
