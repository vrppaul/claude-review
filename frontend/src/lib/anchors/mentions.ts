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
import { anchorMentionedIn, anchorToken } from '$lib/anchors/views';

// An @ and whatever has been typed after it, running up to the caret: a mention not finished yet
const MENTION_BEING_TYPED = /@([^\s@]*)$/;
// Two spaces or more, left in the words where a token was taken out
const GAP_LEFT = / {2,}/g;

/** What a message says, and where its caret is. */
export interface TypedText {
	text: string;
	caret: number;
}

/** The threads a message points at, as its text stands right now. */
export function threadsIn(text: string, threads: Thread[]): Thread[] {
	return threads.filter((thread) => anchorMentionedIn(text, thread.anchor));
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

/** The message with a thread's token taken out of the words, as if deleted like one. */
export function withoutThread(text: string, thread: Thread): string {
	return text.split(anchorToken(thread.anchor)).join('').replace(GAP_LEFT, ' ');
}

/** The word a message mentions a file by. */
export function fileToken(path: string): string {
	return `@${path}`;
}
