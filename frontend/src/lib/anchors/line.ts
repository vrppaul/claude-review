import type { LineAnchor, LineSide } from '$lib/types';
import type { AnchorView } from '$lib/anchors/views';
import { lineRangeLabel } from '$lib/utils/line-label';

// What may follow a line token inside a longer one: `@a.py:1-2` sits inside
// `@a.py:1-20`, so a digit or a dash after it means it is not this token
const LONGER_TOKEN = /[\d-]/;

function fileName(path: string): string {
	return path.split('/').pop() ?? path;
}

function label(anchor: LineAnchor): string {
	return lineRangeLabel(anchor.side, anchor.start_line, anchor.end_line);
}

function token(anchor: LineAnchor): string {
	return `@${anchor.file}:${anchor.start_line}-${anchor.end_line}`;
}

/** Whether a message mentions these lines by their token, and not a longer one. */
function mentionedIn(text: string, anchor: LineAnchor): boolean {
	const said = token(anchor);
	let from = text.indexOf(said);
	while (from !== -1) {
		const after = text[from + said.length];
		if (after === undefined || !LONGER_TOKEN.test(after)) return true;
		from = text.indexOf(said, from + 1);
	}
	return false;
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

/** How a thread on lines of a file is named, mentioned and told apart. */
export const lineAnchorView: AnchorView<LineAnchor> = {
	label,
	place: (anchor) => `${anchor.file} · ${label(anchor)}`,
	shortPlace: (anchor) => `${fileName(anchor.file)} ${label(anchor)}`,
	token,
	mentionedIn,
	sameSpot,
	fileOf: (anchor) => anchor.file
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
