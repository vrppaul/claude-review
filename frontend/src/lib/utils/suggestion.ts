/**
 * A suggested replacement in a comment: code the reader wants in place of the
 * lines commented on, written as a fenced block the way GitHub writes one.
 * Written by the comment field and read by the thread, in one format, here.
 *
 * A fence of backticks is closed by the first line that is a run of at least
 * as many (CommonMark), so a suggestion is fenced one backtick longer than
 * the longest run inside it: no line of it closes it early, and reading it
 * back by the same rule finds every line of it.
 */

export interface CommentPart {
	kind: 'prose' | 'suggestion';
	text: string;
}

/** A comment with a suggestion put in it, and where the suggested lines stand in it. */
interface Suggested {
	text: string;
	start: number;
	end: number;
}

const BACKTICK = '`';
// The fewest backticks that open a fenced block
const SHORTEST_FENCE = 3;
// Every run of backticks in a text
const BACKTICK_RUNS = /`+/g;
// What a fence opening a suggestion says after its backticks
const SUGGESTION_INFO = 'suggestion';
const LINE_BREAK = '\n';
// Between what was already written and a suggestion put after it: one empty line
const PARAGRAPH_BREAK = '\n\n';
// Each suggestion in a comment: an opening fence on a line of its own, what
// it suggests, and the first line after it that is a run of at least as many
// backticks, spaces after it allowed
const SUGGESTION = /^(?<fence>`{3,})suggestion\n(?<suggested>[\s\S]*?)\n?^\k<fence>`*[ \t]*$/gm;
// The opening fence of a suggestion, on a line of its own
const SUGGESTION_OPENING = /^`{3,}suggestion$/m;

/** Whether a comment suggests a replacement already: one is enough. */
export function hasSuggestion(text: string): boolean {
	return SUGGESTION_OPENING.test(text);
}

/** A comment with these lines suggested after what is written in it. */
export function withSuggestion(written: string, lines: readonly string[]): Suggested {
	const said = written.trim();
	const suggested = lines.join(LINE_BREAK);
	const fence = fenceAround(suggested);
	const opening = `${said ? `${said}${PARAGRAPH_BREAK}` : ''}${fence}${SUGGESTION_INFO}${LINE_BREAK}`;
	return {
		text: `${opening}${suggested}${LINE_BREAK}${fence}`,
		start: opening.length,
		end: opening.length + suggested.length
	};
}

/**
 * Split a comment into what was written and what was suggested.
 *
 * A suggestion is code the reader wants in place of what is there, so it is
 * shown as code rather than as prose in the reading face.
 */
export function splitSuggestions(body: string): CommentPart[] {
	const parts: CommentPart[] = [];
	let at = 0;

	for (const match of body.matchAll(SUGGESTION)) {
		const before = body.slice(at, match.index).trim();
		if (before) parts.push({ kind: 'prose', text: before });
		parts.push({ kind: 'suggestion', text: match.groups?.suggested ?? '' });
		at = match.index + match[0].length;
	}

	const rest = body.slice(at).trim();
	if (rest) parts.push({ kind: 'prose', text: rest });
	return parts.length > 0 ? parts : [{ kind: 'prose', text: body }];
}

/** The fence that sets a text apart as code: one backtick longer than its longest run, and never too short to open. */
function fenceAround(text: string): string {
	const longestRun = Array.from(text.matchAll(BACKTICK_RUNS)).reduce(
		(longest, run) => Math.max(longest, run[0].length),
		0
	);
	return BACKTICK.repeat(Math.max(SHORTEST_FENCE, longestRun + 1));
}
