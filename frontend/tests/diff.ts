/** Diffs as the server hands them over, built with only what a test cares about. */
import { REVIEW_IDENTITY, THIS_RUN } from './fake-socket';
import type { DiffFile, DiffHunk, DiffLine, DiffResponse, ReviewResponse, ShownBase } from '$lib/types';
import { SEND_LIMITS } from './pasted-images';

/** A file as the diff carries it: modified, shown line by line, open to comments, with no lines unless given some. */
export function diffFile(given: Partial<DiffFile> = {}): DiffFile {
	return {
		path: 'file.ts',
		status: 'modified',
		hunks: [],
		unshown: null,
		old_mode: null,
		new_mode: null,
		commentable: true,
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
	return { kind: 'context', old_number: oldNumber, new_number: newNumber, content };
}

export function addedLine(newNumber: number, content: string): DiffLine {
	return { kind: 'add', old_number: null, new_number: newNumber, content };
}

export function removedLine(oldNumber: number, content: string): DiffLine {
	return { kind: 'delete', old_number: oldNumber, new_number: null, content };
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
				{ header: '' }
			)
		]
	});
}

/** The review's own base, as a diff taken against it names it. */
export const REVIEW_BASE: ShownBase = { key: 'review', phrase: 'uncommitted changes', narrowed: false };

/** A base narrower than the review's own: what changed since a round began, as a diff taken against it names it. */
export function sinceRound(round: number): ShownBase {
	return { key: `round:${round}`, phrase: `changes since round ${round}`, narrowed: true };
}

/** The take of the review a test's diff is read at, and its story told of, unless it says another. */
export const FIRST_TAKE = 1;

/** A take after it: what the review holds once its diff was taken again. */
export const A_LATER_TAKE = 2;

/** What the server answers a request for the diff with, around these files. */
export function diffResponse(given: Partial<DiffResponse> = {}): DiffResponse {
	return {
		files: [],
		base: REVIEW_BASE,
		moved: 0,
		take: FIRST_TAKE,
		...given
	};
}

/** What the review a test opens is of, unless it says otherwise. */
export const REVIEW_TITLE = 'repo: uncommitted changes';
/** Where its change is: the repository, on the branch the change is made on. */
const REVIEWED_REPOSITORY: ReviewResponse['repository'] = { name: 'repo', checkout: { at: 'branch', branch: 'main' } };

/** What the server says the review is, as a page opening reads it: a diff in its first round. */
export function reviewResponse(given: Partial<ReviewResponse> = {}): ReviewResponse {
	return {
		title: REVIEW_TITLE,
		repository: REVIEWED_REPOSITORY,
		identity: REVIEW_IDENTITY,
		mode: 'diff',
		round: 1,
		answerer_attached: false,
		agent: { model: null, context: null, at: null },
		work: null,
		takes_a_story: true,
		story_asking: null,
		limits: SEND_LIMITS,
		release: '1.5.0',
		instance: THIS_RUN,
		sequence: 0,
		...given
	};
}
