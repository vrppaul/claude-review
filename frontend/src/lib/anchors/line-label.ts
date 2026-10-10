import type { LinePlace, LineSide } from '$lib/types';

/** One line, inside a sentence: "line 42", or "removed line 42" on the old side. */
export function lineInWords(place: LinePlace): string {
	return `${place.side === 'old' ? 'removed line' : 'line'} ${place.number}`;
}

/**
 * Human label for a commented range: "Line 42", "Lines 42-47", or the
 * "Removed" variants. Comments on the old side point at lines the change
 * deleted, so their numbers refer to the file as it was.
 */
export function lineRangeLabel(side: LineSide, startLine: number, endLine: number): string {
	const removed = side === 'old';
	if (endLine !== startLine) {
		return `${removed ? 'Removed lines' : 'Lines'} ${startLine}-${endLine}`;
	}
	return `${removed ? 'Removed line' : 'Line'} ${startLine}`;
}
