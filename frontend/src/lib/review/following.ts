/**
 * Moving the threads onto a diff taken again, once the server has said where
 * each now hangs: one whose lines survived follows them, and one whose lines
 * are gone is marked rather than left on a line that has become something
 * else.
 */

import { sameSpot } from '$lib/anchors/views';
import type { Anchor, FollowOutcome, Thread } from '$lib/types';

// Said when the server's answer leaves out a thread it was asked to follow, which it never should
const NO_ANCHOR_CAME_BACK = 'The server did not say where every thread now hangs';

/** The threads on their new anchors, and what following did to them. */
interface Followed {
	threads: Thread[];
	outcome: FollowOutcome;
}

/** A thread, and the anchor following the diff gave it. */
interface FollowedThread {
	thread: Thread;
	moved: Anchor;
}

/**
 * The threads as they are now, each one asked about on the anchor the server
 * gave it. One written while the answer was on its way was not asked about
 * and is left as written; one removed meanwhile is gone, and not counted.
 *
 * @param asked the threads whose anchors the server was asked to follow, in the order asked
 * @param anchors the server's answer: one anchor for each thread asked about, in the same order
 * @param current the threads as they are when the answer lands
 */
export function followedThreads(
	asked: readonly Thread[],
	anchors: readonly Anchor[],
	current: readonly Thread[]
): Followed {
	const movedTo = new Map(asked.map((thread, index) => [thread.id, answered(anchors[index])]));
	const followed = current.flatMap((thread) => followedOf(thread, movedTo));
	return {
		threads: current.map((thread) => onItsAnchor(thread, movedTo)),
		outcome: { followed: followed.filter(wentWithItsLines).length, outdated: followed.filter(lostItsLines).length }
	};
}

/** The anchor the answer gave a thread asked about. */
function answered(moved: Anchor | undefined): Anchor {
	if (moved === undefined) throw new Error(NO_ANCHOR_CAME_BACK);
	return moved;
}

/** A thread with the anchor following gave it, if it was asked about. */
function followedOf(thread: Thread, movedTo: ReadonlyMap<string, Anchor>): FollowedThread[] {
	const moved = movedTo.get(thread.id);
	return moved ? [{ thread, moved }] : [];
}

/** A thread on the anchor following gave it, or as it was where it was not asked about. */
function onItsAnchor(thread: Thread, movedTo: ReadonlyMap<string, Anchor>): Thread {
	const moved = movedTo.get(thread.id);
	return moved ? { ...thread, anchor: moved } : thread;
}

/** Whether following took a thread off lines it still had. */
function lostItsLines({ thread, moved }: FollowedThread): boolean {
	return moved.outdated && !thread.anchor.outdated;
}

/** Whether following took a thread, with its lines, somewhere else. */
function wentWithItsLines(followed: FollowedThread): boolean {
	return !lostItsLines(followed) && !sameSpot(followed.moved, followed.thread.anchor);
}
