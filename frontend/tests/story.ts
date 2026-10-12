/** Stories as the review hands them to its page, built with only what a test cares about. */
import type { StoryHeld, ToldChapter, ToldStep, ToldStory } from '$lib/types';
import { addedLine, diffFile, hunk } from './diff';

/** The round a story is told in, unless a test says another. */
const FIRST_ROUND = 1;

/** A step that shows one line a file gained, and says why if it is given a reason. */
export function toldStep(file: string, line: number, reason: string | null = null): ToldStep {
	const piece = diffFile({
		path: file,
		hunks: [hunk([addedLine(line, `line ${line} of ${file}`)], { header: '', old_start: line, new_start: line })]
	});
	return { file, lines: { first: line, last: line }, reason, piece };
}

/** A chapter of these steps, known by its id. */
export function toldChapter(id: string, steps: ToldStep[], given: Partial<ToldChapter> = {}): ToldChapter {
	return { id, title: `Chapter ${id}`, why: `Why the changes of ${id} belong together.`, doubt: null, steps, ...given };
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

/** A story as the review holds it: as told, in the round it was told in. */
export function storyHeld(given: Partial<ToldStory> = {}, round = FIRST_ROUND): StoryHeld {
	return { story: toldStory(given), round };
}
