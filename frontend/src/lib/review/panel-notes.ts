/**
 * What the review says in the panel about what it did itself — a retake, a
 * thread raised, a gap in what the server could hand over — between what
 * was said there. Worded here, once, so the code that notes one only says
 * which.
 */

import { anchorShortPlace } from '$lib/anchors/views';
import { followWords, PHRASE_BREAK } from '$lib/review/follow-words';
import type { Anchor, FollowOutcome } from '$lib/types';
import { messageOf } from '$lib/utils/errors';
import { counted, FILES } from '$lib/utils/words';

// Pushes were missed that the server could not hand over again
const CONNECTION_LOST = 'connection lost for a while — anything said meanwhile may be missing';
// The threads a draft brought back, followed onto the diff the review opened on
const KEPT_THREADS = 'threads picked up from the draft';

/** The diff taken again: how many files the review holds now, and what following the threads did. */
export function retakenNote(fileCount: number, moved: FollowOutcome): string {
	return [`diff retaken · ${counted(fileCount, FILES)}`, ...followWords(moved)].join(PHRASE_BREAK);
}

export function diffNotTakenNote(error: unknown): string {
	return `the diff could not be taken again — ${messageOf(error)}`;
}

export function storyNotReadNote(error: unknown): string {
	return `the story could not be read — ${messageOf(error)}`;
}

export function storyNotFollowedNote(error: unknown): string {
	return `the threads could not follow the story told — ${messageOf(error)}`;
}

export function storyNotAskedForNote(error: unknown): string {
	return `the story could not be asked for — ${messageOf(error)}`;
}

export function storyNotStoppedNote(error: unknown): string {
	return `the story could not be stopped — ${messageOf(error)}`;
}

/** A thread the agent raised, by where it hangs. */
export function raisedNote(anchor: Anchor): string {
	return `pointed at ${anchorShortPlace(anchor)}`;
}

/** Caught up after a gap: what may be missing, and what following the threads did. */
export function caughtUpNote(moved: FollowOutcome): string {
	return [CONNECTION_LOST, ...followWords(moved)].join(PHRASE_BREAK);
}

/** Catching up after a gap failed somewhere: reading the review again, or moving the threads. */
export function notCaughtUpNote(error: unknown): string {
	return `${CONNECTION_LOST} — and catching up failed: ${messageOf(error)}`;
}

/** The threads a draft brought back, followed onto the diff: what moved, or nothing to say when none did. */
export function keptThreadsFollowedNote(moved: FollowOutcome): string | null {
	const words = followWords(moved);
	return words.length === 0 ? null : [KEPT_THREADS, ...words].join(PHRASE_BREAK);
}

export function keptThreadsNotFollowedNote(error: unknown): string {
	return `${KEPT_THREADS} could not follow the diff — ${messageOf(error)}`;
}
