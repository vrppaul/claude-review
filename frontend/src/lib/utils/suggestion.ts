/**
 * A suggested replacement in a comment: code the reader wants in place of the
 * lines commented on, written as a fenced block the way GitHub writes one.
 * Written by the comment field and read by the thread, in one format, here.
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

// What opens a suggestion, on a line of its own, and what closes it, on the line after its last
const SUGGESTION_FENCE = '```suggestion';
const FENCE_CLOSE = '```';
const LINE_BREAK = '\n';
// Between what was already written and a suggestion put after it: one empty line
const PARAGRAPH_BREAK = '\n\n';
// Each suggestion in a comment, up to the first fence that closes it
const SUGGESTION = new RegExp(`${SUGGESTION_FENCE}${LINE_BREAK}[\\s\\S]*?${FENCE_CLOSE}`, 'g');
// The line break a suggestion's last line ends with before its closing fence
const LAST_LINE_BREAK = /\n$/;

/** Whether a comment suggests a replacement already: one is enough. */
export function hasSuggestion(text: string): boolean {
	return text.includes(SUGGESTION_FENCE);
}

/** A comment with these lines suggested after what is written in it. */
export function withSuggestion(written: string, lines: readonly string[]): Suggested {
	const said = written.trim();
	const opening = `${said ? `${said}${PARAGRAPH_BREAK}` : ''}${SUGGESTION_FENCE}${LINE_BREAK}`;
	const suggested = lines.join(LINE_BREAK);
	return {
		text: `${opening}${suggested}${LINE_BREAK}${FENCE_CLOSE}`,
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
		const [block] = match;
		const before = body.slice(at, match.index).trim();
		if (before) parts.push({ kind: 'prose', text: before });
		const suggested = block.slice(SUGGESTION_FENCE.length + LINE_BREAK.length, -FENCE_CLOSE.length);
		parts.push({ kind: 'suggestion', text: suggested.replace(LAST_LINE_BREAK, '') });
		at = match.index + block.length;
	}

	const rest = body.slice(at).trim();
	if (rest) parts.push({ kind: 'prose', text: rest });
	return parts.length > 0 ? parts : [{ kind: 'prose', text: body }];
}
