/**
 * What handing this review over would cost, in tokens.
 *
 * This is the one number of the two in the panel that can be worked out
 * here: the review is the diff on screen and the threads written against
 * it, and both are in hand. The agent's own context cannot be measured from
 * this side at all, which is why it arrives as a report rather than a
 * measurement. The diff and the threads are counted apart: the threads
 * change far more often, and a long diff is not counted again for each.
 */

import type { Thread, DiffFile } from '$lib/types';

// Characters per token, roughly, for English prose and code alike. Close
// enough for the only question the number answers: is handing this over
// cheap, or is it most of what an agent can hold at once.
const CHARS_PER_TOKEN = 4;

/** The characters the diff on screen hands over: every path, and every line with its break. */
export function diffCharacters(files: DiffFile[]): number {
	let characters = 0;
	for (const file of files) {
		characters += file.path.length;
		for (const hunk of file.hunks) {
			for (const line of hunk.lines) characters += line.content.length + 1;
		}
	}
	return characters;
}

/** The characters the threads hand over: what each says, and the lines it quotes. */
export function threadCharacters(threads: Thread[]): number {
	let characters = 0;
	for (const thread of threads) {
		characters += thread.body.length;
		for (const turn of thread.turns) characters += turn.body.length;
		for (const line of thread.anchor.quote) characters += line.length;
	}
	return characters;
}

/** What handing over this many characters costs, in tokens. */
export function tokensOf(characters: number): number {
	return Math.round(characters / CHARS_PER_TOKEN);
}

// Counts this large are said in thousands, to one decimal place: "~18.2k"
const THOUSAND = 1000;
const TENTHS = 10;

/** The same number as the panel says it: "~18.2k", "~900". */
export function formatWeight(tokens: number): string {
	if (tokens < THOUSAND) return `~${tokens}`;
	return `~${Math.round(tokens / (THOUSAND / TENTHS)) / TENTHS}k`;
}
