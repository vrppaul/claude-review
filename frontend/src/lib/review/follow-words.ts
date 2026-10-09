/**
 * What moving the threads onto a retaken diff did, in words: said in the
 * retake bar and in the panel alike, so the two never word it differently.
 */

import type { FollowOutcome } from '$lib/types';

/** What stands between the phrases of one note. */
export const PHRASE_BREAK = ' · ';

/** What following the threads did, one phrase per thing it did, and none where it did nothing. */
export function followWords({ followed, outdated }: FollowOutcome): string[] {
	const words: string[] = [];
	if (followed > 0)
		words.push(`${followed} ${followed === 1 ? 'thread followed its' : 'threads followed their'} lines`);
	if (outdated > 0) words.push(`${outdated} ${outdated === 1 ? 'is' : 'are'} outdated`);
	return words;
}
