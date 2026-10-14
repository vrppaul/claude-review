import type { LineAnchor, LineSide } from '$lib/types';
import type { AnchorView } from '$lib/anchors/views';
import { lineRangeLabel } from '$lib/anchors/line-label';
import { mentionStarts } from '$lib/anchors/token-mentions';
import { fileName } from '$lib/utils/paths';

// What carries a line token on into a longer one: `@a.py:1-2` sits inside
// `@a.py:1-20`, so a digit or a dash after it means it is not this token
const CARRIES_ON = /^[\d-]/;

function label(anchor: LineAnchor): string {
	return lineRangeLabel(anchor.side, anchor.start_line, anchor.end_line);
}

function token(anchor: LineAnchor): string {
	return `@${anchor.file}:${anchor.start_line}-${anchor.end_line}`;
}

/** Whether two anchors hang on the same lines, on the same side of the same file. */
function sameSpot(one: LineAnchor, other: LineAnchor): boolean {
	return (
		one.file === other.file &&
		one.side === other.side &&
		one.start_line === other.start_line &&
		one.end_line === other.end_line
	);
}

/**
 * How a thread on lines of a file is named, mentioned and told apart. It was
 * written against the lines it quotes, and a suggestion in it replaces them.
 */
export const lineAnchorView: AnchorView<LineAnchor> = {
	label,
	place: (anchor) => `${anchor.file} · ${label(anchor)}`,
	shortPlace: (anchor) => `${fileName(anchor.file)} ${label(anchor)}`,
	token,
	mentionsIn: (text, anchor) => mentionStarts(text, token(anchor), CARRIES_ON),
	sameSpot,
	writtenAgainst: (anchor) => anchor.quote,
	replaces: (anchor) => anchor.quote,
	placeOf: (anchor) => ({ on: 'lines', lines: anchor })
};

/** Lines of a file as the reader selects them, with what they say now. */
export function lineAnchor(
	file: string,
	side: LineSide,
	startLine: number,
	endLine: number,
	quote: string[]
): LineAnchor {
	return {
		kind: 'line',
		file,
		side,
		start_line: startLine,
		end_line: endLine,
		quote,
		outdated: false
	};
}
