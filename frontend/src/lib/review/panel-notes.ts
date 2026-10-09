/**
 * What the review says in the panel about what it did itself — a retake, a
 * thread raised, a gap in what the server could hand over — between what
 * was said there. Worded here, once, so the code that notes one only says
 * which.
 */

import { anchorShortPlace } from '$lib/anchors/views';
import { followWords, PHRASE_BREAK } from '$lib/review/follow-words';
import type { Anchor, FollowOutcome } from '$lib/types';

// Pushes were missed that the server could not hand over again
const CONNECTION_LOST = 'connection lost for a while — anything said meanwhile may be missing';
// What the reader can do about a failure nobody gave a reason for
const NO_REASON = 'reload the review';

/** Why something failed, in the words it failed with, or what to do about it. */
function reasonOf(error: unknown): string {
	return error instanceof Error ? error.message : NO_REASON;
}

/** The diff taken again: how many files the review holds now, and what following the threads did. */
export function retakenNote(fileCount: number, moved: FollowOutcome): string {
	const files = `${fileCount} ${fileCount === 1 ? 'file' : 'files'}`;
	return [`diff retaken · ${files}`, ...followWords(moved)].join(PHRASE_BREAK);
}

export function diffNotTakenNote(error: unknown): string {
	return `the diff could not be taken again — ${reasonOf(error)}`;
}

/** A thread the agent raised, by where it hangs. */
export function raisedNote(anchor: Anchor): string {
	return `pointed at ${anchorShortPlace(anchor)}`;
}

/** Caught up after a gap: what may be missing, and what following the threads did. */
export function caughtUpNote(moved: FollowOutcome): string {
	return [CONNECTION_LOST, ...followWords(moved)].join(PHRASE_BREAK);
}

export function notCaughtUpNote(error: unknown): string {
	return `${CONNECTION_LOST} — and the review could not be read again: ${reasonOf(error)}`;
}
