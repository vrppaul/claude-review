/**
 * A hunk read as what it kept and what it replaced.
 *
 * A run of removed lines and the run of added lines right after it are one
 * replacement, read in order: the first removed line was replaced by the
 * first added one, and so on as far as the shorter run goes. Added lines with
 * no removal before them, or removals with nothing added after, are a
 * replacement with one side empty. The two-column layout and the marks on
 * changed words both read a hunk this way, so a line is always faced with the
 * line it is marked against.
 */

import type { DiffLine } from '$lib/types';

/** Lines the change replaced, and the lines it put in their place, each in order. */
interface Replacement<Line> {
	kind: 'replaced';
	removed: Line[];
	added: Line[];
}

/** A line the change kept, or a run of lines it replaced. */
export type Run<Line> = { kind: 'kept'; line: Line } | Replacement<Line>;

/**
 * The runs of a hunk's lines, in order.
 *
 * @param lines the hunk's lines, as whichever stage of drawing holds them
 */
export function runsOf<Line extends { readonly line: DiffLine }>(lines: readonly Line[]): Run<Line>[] {
	const runs: Run<Line>[] = [];
	let replacing: Replacement<Line> | null = null;
	for (const held of lines) {
		const { kind } = held.line;
		if (kind === 'context') {
			runs.push({ kind: 'kept', line: held });
			replacing = null;
			continue;
		}
		// A removal after additions is the start of the next replacement
		if (replacing === null || (kind === 'delete' && replacing.added.length > 0)) {
			replacing = { kind: 'replaced', removed: [], added: [] };
			runs.push(replacing);
		}
		if (kind === 'delete') replacing.removed.push(held);
		else replacing.added.push(held);
	}
	return runs;
}
