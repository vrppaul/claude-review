/**
 * Where a thread hangs, as the review's threads sort them out for whoever
 * draws them: on lines of a file, or on a block of the story's words; and
 * what a comment started on either hangs on once it is written.
 */

import { lineAnchor } from '$lib/anchors/line';
import { blockKey, storyAnchor } from '$lib/anchors/story';
import { threadPlaceOf, type ThreadOnLines } from '$lib/anchors/views';
import type { Anchor, Thread, WrittenOnLines, WrittenOnTheStory } from '$lib/types';

/** A thread on a block of the story, with what its block is known by. */
export interface ThreadOnBlock {
	thread: Thread;
	block: string;
}

/** A thread with the lines of a file it hangs on; nothing for one drawn elsewhere. */
export function withItsLines(thread: Thread): ThreadOnLines[] {
	const place = threadPlaceOf(thread.anchor);
	return place.on === 'lines' ? [{ thread, lines: place.lines }] : [];
}

/** A thread with what the block of the story it hangs on is known by; nothing for one drawn elsewhere. */
export function withItsBlock(thread: Thread): ThreadOnBlock[] {
	const place = threadPlaceOf(thread.anchor);
	return place.on === 'story' ? [{ thread, block: blockKey(place.block) }] : [];
}

/** What a comment started on lines or on a block of the story hangs on, once it is written. */
export function anchorWrittenOn(at: WrittenOnLines | WrittenOnTheStory): Anchor {
	switch (at.kind) {
		case 'new': {
			const { side, startLine, endLine } = at.lines;
			return lineAnchor(at.file, side, startLine, endLine, at.quote);
		}
		case 'story':
			return storyAnchor(at.block, at.words);
	}
}
