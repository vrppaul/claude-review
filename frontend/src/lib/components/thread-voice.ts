/**
 * Whose words are whose, by the colour they are said in: a turn's are
 * whoever said it, and a thread's whoever raised it — the agent's where the
 * agent raised it, the reader's otherwise. The tag of what a question asks
 * for and the field to reply in are both said in the thread's.
 */

import type { Thread, TurnAuthor } from '$lib/types';
import type { Voice } from '$lib/ui/voice';
import { AGENT, READER } from '$lib/utils/speakers';

/** The voice each author of a turn speaks in. */
export const TURN_VOICES: Record<TurnAuthor, Voice> = { [READER]: 'reader', [AGENT]: 'agent' };

/** The voice of whoever raised the thread. */
export function threadVoice(thread: Thread): Voice {
	return TURN_VOICES[thread.raised_by];
}
