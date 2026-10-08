/** Diffs as the server hands them over, built with only what a test cares about. */
import type { DiffFile, DiffHunk, DiffLine, DiffResponse } from '$lib/types';
import { SEND_LIMITS } from './pasted-images';

/** A file as the diff carries it: modified, text, with no lines unless given some. */
export function diffFile(given: Partial<DiffFile> = {}): DiffFile {
	return {
		path: 'file.ts',
		status: 'modified',
		hunks: [],
		is_binary: false,
		old_mode: null,
		new_mode: null,
		...given
	};
}

/** A hunk of these lines, at the top of the file unless placed elsewhere. */
export function hunk(lines: DiffLine[], placed: Partial<Omit<DiffHunk, 'lines'>> = {}): DiffHunk {
	return { header: '@@ -1 +1 @@', old_start: 1, new_start: 1, lines, ...placed };
}

/**
 * A line the change left alone. A plain file, a transcript, has no old
 * version, so its lines carry no old number.
 */
export function contextLine(oldNumber: number | null, newNumber: number, content: string): DiffLine {
	return { type: 'context', old_no: oldNumber, new_no: newNumber, content };
}

export function addedLine(newNumber: number, content: string): DiffLine {
	return { type: 'add', old_no: null, new_no: newNumber, content };
}

export function removedLine(oldNumber: number, content: string): DiffLine {
	return { type: 'delete', old_no: oldNumber, new_no: null, content };
}

/**
 * A file read whole rather than as a change: a plan, a doc, one message of a
 * transcript. It has no old version, so neither a header nor old numbers.
 */
export function wholeFile(path: string, ...lines: string[]): DiffFile {
	return diffFile({
		path,
		status: 'added',
		hunks: [
			hunk(
				lines.map((line, index) => contextLine(null, index + 1, line)),
				{ header: '', old_start: 0 }
			)
		]
	});
}

/** What the server answers a request for the diff with, around these files. */
export function diffResponse(given: Partial<DiffResponse> = {}): DiffResponse {
	return {
		files: [],
		mode: 'diff',
		title: 'repo: uncommitted changes',
		phrase: 'uncommitted changes',
		round: 1,
		answerer_attached: false,
		agent: { model: null, context: null, at: null },
		moved: 0,
		limits: SEND_LIMITS,
		release: '1.5.0',
		...given
	};
}
