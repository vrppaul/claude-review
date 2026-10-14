/**
 * What a field says before anything is written in it, by what is written
 * there. Written once, for the field and for whatever offers it: a thread
 * offers a reply in a field drawn as the field it opens, saying the same.
 */

import type { WrittenAt } from '$lib/types';

// A reply reads as a turn of the conversation, and a comment on the story's words as the offer that opened it
export const PLACEHOLDERS: Record<WrittenAt['kind'], string> = {
	new: 'What should change here?',
	story: 'Ask about this…',
	edit: 'What should change here?',
	reply: 'Reply…'
};
