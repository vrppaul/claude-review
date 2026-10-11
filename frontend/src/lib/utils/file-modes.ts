/**
 * A change of a file's mode, in words.
 *
 * Git keeps what a path is in its mode: a link and a submodule have modes
 * of their own, and every other mode is a file, executable or not. A change
 * from one kind to another turns the path into something else — a file
 * into a link — and is said that way; a change between two modes of a file
 * is a change of its permissions, said by the modes themselves.
 */

import type { DiffFile } from '$lib/types';

/** What changed about a path's mode: what it is, or who may run it. */
type ModeChangeKind = 'Type' | 'Permission';

/** A mode change as a file's notes say it: what changed, from what, to what. */
export interface ModeChange {
	what: ModeChangeKind;
	from: string;
	to: string;
}

// What a path is, by the modes git gives the things that are not files
const KIND_OF_MODE: Readonly<Record<string, string>> = { '120000': 'link', '160000': 'submodule' };
// What every other mode is
const A_FILE = 'file';

function kindOf(mode: string): string {
	return KIND_OF_MODE[mode] ?? A_FILE;
}

/** How a file's mode changed, if it did. */
export function modeChangeOf(file: DiffFile): ModeChange | null {
	if (file.old_mode === null || file.new_mode === null) return null;
	const [before, after] = [kindOf(file.old_mode), kindOf(file.new_mode)];
	if (before !== after) return { what: 'Type', from: before, to: after };
	return { what: 'Permission', from: file.old_mode, to: file.new_mode };
}
