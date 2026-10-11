/**
 * How a panel message points at threads and files.
 *
 * The token is the reference: one word in the text, deleted like any other
 * word, and read back at the moment of sending. Nothing is kept beside the
 * text, so a token typed by hand works exactly as one the picker inserted,
 * and editing the message cannot leave a reference behind that the words no
 * longer mention.
 */

import type { Thread } from '$lib/types';
import { anchorMentionsIn, anchorToken } from '$lib/anchors/views';

// An @ and whatever has been typed after it, running up to the caret: a mention not finished yet
const MENTION_BEING_TYPED = /@([^\s@]*)$/;
// The space a word stands apart by: taken out with a token, as a deleted word takes one
const WORD_SPACE = ' ';

/** What a message says, and where its caret is. */
export interface TypedText {
	text: string;
	caret: number;
}

/** The threads a message points at, as its text stands right now. */
export function threadsIn(text: string, threads: Thread[]): Thread[] {
	return threads.filter((thread) => anchorMentionsIn(text, thread.anchor).length > 0);
}

/** What has been typed after an @ that runs up to the caret, if one does. */
export function mentionBeingTyped({ text, caret }: TypedText): string | null {
	return MENTION_BEING_TYPED.exec(text.slice(0, caret))?.[1] ?? null;
}

/**
 * The message with a token put where the caret is — in place of the mention
 * being typed there, if there is one — and a space after it, so typing goes
 * on; and where the caret goes then.
 */
export function withMention({ text, caret }: TypedText, token: string): TypedText {
	const before = text.slice(0, caret).replace(MENTION_BEING_TYPED, '');
	const said = `${token} `;
	return { text: `${before}${said}${text.slice(caret)}`, caret: before.length + said.length };
}

/**
 * The message with a thread's token taken out of the words, as if deleted
 * like one: each mention of it with one space beside it, and nothing of a
 * longer token that starts the same, nor of any other space — code typed
 * into the message keeps its indentation.
 */
export function withoutThread(text: string, thread: Thread): string {
	const length = anchorToken(thread.anchor).length;
	return cutOut(text, anchorMentionsIn(text, thread.anchor), length);
}

/** Where a cut of a text starts and ends, the end left out. */
interface Cut {
	start: number;
	end: number;
}

/** A text with the token standing at each of these places, this long, cut out of it with one space beside it. */
function cutOut(text: string, starts: number[], length: number): string {
	const kept: string[] = [];
	let from = 0;
	for (const start of starts) {
		const cut = withOneSpace(text, { start, end: start + length });
		kept.push(text.slice(from, cut.start));
		from = cut.end;
	}
	kept.push(text.slice(from));
	return kept.join('');
}

/** A token's cut, widened by the space after it — or, where none follows, by the one before it. */
function withOneSpace(text: string, token: Cut): Cut {
	if (text[token.end] === WORD_SPACE) return { start: token.start, end: token.end + 1 };
	if (text[token.start - 1] === WORD_SPACE) return { start: token.start - 1, end: token.end };
	return token;
}

/** The word a message mentions a file by. */
export function fileToken(path: string): string {
	return `@${path}`;
}
