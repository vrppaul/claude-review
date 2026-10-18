/** Stories as the review hands them to its page, built with only what a test cares about. */
import type { ReviewStory } from '$lib/review/review-story.svelte';
import type {
	DiffFile,
	FollowedChapter,
	FollowedStep,
	StoryAsking,
	StoryHeld,
	StoryResponse,
	ToldStory
} from '$lib/types';
import { addedLine, diffFile, FIRST_TAKE, hunk } from './diff';

/** The round a story is told in, unless a test says another. */
const FIRST_ROUND = 1;
/** The round a round's work moved the code on under a story in, unless a test says another. */
const SECOND_ROUND = FIRST_ROUND + 1;

/** That a round moved the code on under a story, as the review says it. */
type CodeMovedOn = NonNullable<StoryHeld['moved_on']>;
/** The lines of a file a step was told on, or stands at now: the first and the last, both among them. */
type StepLines = FollowedStep['lines'];

/** The piece of a file that shows the lines it gained from one to another, both among them. */
export function gainedPiece(file: string, first: number, last: number): DiffFile {
	const gained = Array.from(Array(last - first + 1).keys(), (offset) => first + offset);
	return diffFile({
		path: file,
		hunks: [
			hunk(
				gained.map((line) => addedLine(line, `line ${line} of ${file}`)),
				{ header: '', old_start: first, new_start: first }
			)
		]
	});
}

/**
 * A step that shows the lines a file gained from one to another, both among
 * them, and says why if it is given a reason: its code as it was told.
 */
export function toldStepOfLines(file: string, first: number, last: number, reason: string | null = null): FollowedStep {
	const lines = { first, last };
	const now = { lines, piece: gainedPiece(file, first, last), changed_since_told: false };
	return { file, lines, reason, now, commentable: true, shows_changed_code: false };
}

/** A step that shows one line a file gained, and says why if it is given a reason. */
export function toldStep(file: string, line: number, reason: string | null = null): FollowedStep {
	return toldStepOfLines(file, line, line, reason);
}

/**
 * A step told of some lines of a file, with no reason, whose code stands at
 * these lines now, in this piece, as it was told: a round's work moved it,
 * or the piece is one a test made.
 */
export function stepStandingAt(file: string, told: StepLines, now: StepLines, piece: DiffFile): FollowedStep {
	const standing = { lines: now, piece, changed_since_told: false };
	return { file, lines: told, reason: null, now: standing, commentable: true, shows_changed_code: false };
}

/** A step that shows one line a file gained, which a round's work changed after it was told. */
export function changedStep(file: string, line: number, reason: string | null = null): FollowedStep {
	const lines = { first: line, last: line };
	const now = { lines, piece: gainedPiece(file, line, line), changed_since_told: true };
	return { file, lines, reason, now, commentable: true, shows_changed_code: true };
}

/**
 * A step told of one line a file gained whose code a round took out of the
 * change, as the review says it: standing nowhere.
 */
export function stepWithoutCode(file: string, line: number, reason: string | null = null): FollowedStep {
	const lines = { first: line, last: line };
	return { file, lines, reason, now: null, commentable: true, shows_changed_code: false };
}

/** A chapter of these steps, known by its id, none of whose steps a round changed unless a test says how many. */
export function toldChapter(id: string, steps: FollowedStep[], given: Partial<FollowedChapter> = {}): FollowedChapter {
	return {
		id,
		title: `Chapter ${id}`,
		why: `Why the changes of ${id} belong together.`,
		doubt: null,
		steps,
		changed_steps: 0,
		...given
	};
}

/** A story of one chapter and one step, told from memory, leaving nothing out. */
export function toldStory(given: Partial<ToldStory> = {}): ToldStory {
	return {
		title: 'A change, told',
		told_from: 'memory',
		overview: {
			task: 'What was asked.',
			done: 'What was done.',
			doubt: null,
			diagram: null,
			decisions: [],
			turned_down: [],
			later: []
		},
		chapters: [toldChapter('ch-1', [toldStep('a.py', 1)])],
		housekeeping: [],
		left_out: [],
		...given
	};
}

/**
 * A story as the review holds it: as told, in the first round, of the take
 * a test's diff is read at, its code not moved on, unless it is held otherwise.
 */
export function storyHeld(given: Partial<ToldStory> = {}, held: Partial<Omit<StoryHeld, 'story'>> = {}): StoryHeld {
	return { story: toldStory(given), round: FIRST_ROUND, take: FIRST_TAKE, moved_on: null, ...held };
}

/**
 * That the second round moved the code on under a story, leaving out as
 * much as when it was told, unless a test says otherwise.
 */
export function codeMovedOn(given: Partial<CodeMovedOn> = {}): CodeMovedOn {
	return { round: SECOND_ROUND, left_out: null, ...given };
}

/** What the review answers of its story: none told, unless a test says one was. */
export function storyResponse(given: Partial<StoryResponse> = {}): StoryResponse {
	return { held: null, ...given };
}

/** Read the story the review holds and hold it, as a page does that reads nothing beside it. */
export async function readTheStoryAgain(story: ReviewStory): Promise<void> {
	const hold = await story.read();
	hold();
}

/**
 * When the reader asked for a story: ten seconds past four minutes past
 * one in the afternoon, wherever the tests are run, so a test can say what
 * the page says of that moment. And when an agent took the request, two
 * seconds later.
 */
export const ASKED_AT = new Date(2026, 9, 14, 13, 4, 10).getTime();
export const TAKEN_AT = ASKED_AT + 2_000;

/** The asking for a story as the review says it stands: asked for and taken by no agent yet. */
export const ASKED: StoryAsking = { asked_at: ASKED_AT, taken_at: null, stopped: false };
/** Asked for, and the request taken by an agent. */
export const TAKEN: StoryAsking = { asked_at: ASKED_AT, taken_at: TAKEN_AT, stopped: false };
/** Stopped by the reader, before any agent took the request. */
export const STOPPED: StoryAsking = { asked_at: ASKED_AT, taken_at: null, stopped: true };
