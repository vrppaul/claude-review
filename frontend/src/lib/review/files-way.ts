/**
 * The review read as Files: the change's files, read against a base, and
 * each file of the take the change did not touch, read alone.
 *
 * Where a thread on lines is read in it is decided here once, from what its
 * anchor says of how it stands and from the review's own diff, so the
 * views, the tree and the walk of n and p cannot place one thread apart.
 * No file is read to decide it.
 */

import { inDiffOrder, isDrawn, threadsOffTheDiff, type ThreadsOffTheDiff } from '$lib/anchors/placement';
import type { ThreadLines } from '$lib/anchors/views';
import type { ReviewDiff } from '$lib/review/review-diff.svelte';
import type { Threads } from '$lib/review/threads.svelte';
import type { Thread } from '$lib/types';

/**
 * Where a thread on lines is read among the files:
 * - in-the-change: in its file among the change's files, which the review's own diff holds
 * - above-the-files: above the change's files, which draw no file for it: its file is gone from the take, or its
 *   change is whitespace alone and the diff on screen, with whitespace left out, leaves the file out
 * - in-its-file-alone: in its file read alone, which the change did not touch and the take holds
 */
export type ReadAmongTheFiles = 'in-the-change' | 'above-the-files' | 'in-its-file-alone';

// Where in a file read alone a thread whose lines it does not draw hangs: at the file's head, before its first line
const HEAD_OF_THE_FILE = 0;

/**
 * Where a thread on these lines is read among the files. Under a narrower
 * base a file the change holds and the diff on screen leaves out is the
 * base's to say (`drawnByTheChange`), and its threads are the change's still.
 */
export function whereRead(lines: ThreadLines, diff: ReviewDiff): ReadAmongTheFiles {
	if (!diff.holds(lines.file)) return lines.standing === 'file_gone' ? 'above-the-files' : 'in-its-file-alone';
	return diff.narrowed || diff.shows(lines.file) ? 'in-the-change' : 'above-the-files';
}

/**
 * Whether the change's files on screen draw a thread on these lines. Read
 * against the review's own base they draw every thread not read alone:
 * under its line, at the head of its file, or above the files. A narrower
 * base draws only those on lines it shows whose numbers are the review's
 * own; the rest are drawn once the whole review is put back.
 */
export function drawnByTheChange(lines: ThreadLines, diff: ReviewDiff): boolean {
	if (whereRead(lines, diff) === 'in-its-file-alone') return false;
	return !diff.narrowed || isDrawn(lines, diff.files, diff.numbering);
}

/** The threads drawn above the change's files, by file: none under a narrower base, whose notice names them. */
export function threadsAboveTheFiles(threads: Threads, diff: ReviewDiff): ThreadsOffTheDiff[] {
	if (diff.narrowed) return [];
	const above = threads.onLines.filter(({ lines }) => whereRead(lines, diff) === 'above-the-files');
	return threadsOffTheDiff(above, diff.files);
}

/** The order the tree lists the files the change did not touch in, and n and p walk them: by path. */
function byPath(one: string, other: string): number {
	return one.localeCompare(other);
}

/** The line a thread hangs under in a file read alone: its last, or the file's head where its lines are not drawn. */
function lineHungUnder(lines: ThreadLines): number {
	return lines.side === 'new' && lines.standing === 'on_its_lines' ? lines.end_line : HEAD_OF_THE_FILE;
}

/**
 * The threads as n and p walk them, whichever file of the Files way of
 * reading is on screen: those above the change's files, then the change's
 * down the diff, then those on the files the change did not touch, file by
 * file as the tree lists them, each down its lines.
 */
export function threadsInFilesOrder(threads: Threads, diff: ReviewDiff): Thread[] {
	const byTheChange = threads.onLines.filter(({ lines }) => drawnByTheChange(lines, diff));
	const readAlone = threads.onLines
		.filter(({ lines }) => whereRead(lines, diff) === 'in-its-file-alone')
		.toSorted(
			(one, other) => byPath(one.lines.file, other.lines.file) || lineHungUnder(one.lines) - lineHungUnder(other.lines)
		)
		.map(({ thread }) => thread);
	return [...inDiffOrder(byTheChange, diff.files), ...readAlone];
}

/**
 * The files the change did not touch that the tree lists, by path: the one
 * read alone, while it is, and every one a thread is read in or a comment
 * is being written on.
 */
export function filesOutsideTheChange(threads: Threads, diff: ReviewDiff, readAlone: string | null): string[] {
	const threadsIn = threads.onLines.flatMap(({ lines }) =>
		whereRead(lines, diff) === 'in-its-file-alone' ? [lines.file] : []
	);
	const writtenOn = threads.writing.fields.flatMap(({ at }) =>
		at.kind === 'new' && !diff.holds(at.file) ? [at.file] : []
	);
	const shown = readAlone === null ? [] : [readAlone];
	return [...new Set([...shown, ...threadsIn, ...writtenOn])].toSorted(byPath);
}
