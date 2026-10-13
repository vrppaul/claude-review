/**
 * What moving the threads onto a retaken diff did, in words: said in the
 * retake bar and in the panel alike, so the two never word it differently.
 */

import type { FollowOutcome } from '$lib/types';
import { counted, type CountedWords } from '$lib/utils/words';

/** What stands between the phrases of one note. */
export const PHRASE_BREAK = ' · ';

// What is said of the threads that followed their lines, and of those left on lines that are gone
const FOLLOWED: CountedWords = { one: 'thread followed its', many: 'threads followed their' };
const OUTDATED: CountedWords = { one: 'is', many: 'are' };

/** What following the threads did, one phrase per thing it did, and none where it did nothing. */
export function followWords({ followed, outdated }: FollowOutcome): string[] {
	const words: string[] = [];
	if (followed > 0) words.push(`${counted(followed, FOLLOWED)} lines`);
	if (outdated > 0) words.push(`${counted(outdated, OUTDATED)} outdated`);
	return words;
}
