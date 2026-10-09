/**
 * How a panel message points at threads.
 *
 * The token is the reference: one word in the text, deleted like any other
 * word, and read back at the moment of sending. Nothing is kept beside the
 * text, so a token typed by hand works exactly as one the picker inserted,
 * and editing the message cannot leave a reference behind that the words no
 * longer mention.
 */

import type { Thread } from '$lib/types';
import { anchorMentionedIn } from '$lib/anchors/views';

/** The threads a message points at, as its text stands right now. */
export function threadsIn(text: string, threads: Thread[]): Thread[] {
	return threads.filter((thread) => anchorMentionedIn(text, thread.anchor));
}
