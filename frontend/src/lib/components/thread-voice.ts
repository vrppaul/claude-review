/**
 * Whose a thread is, by the colour what is said in it takes: the agent's
 * where the agent raised it, the reader's otherwise. The tag of what a
 * question asks for and the field to reply in are both said in it.
 */

import type { Thread } from '$lib/types';
import type { Voice } from '$lib/ui/voice';
import { raisedByAgent } from '$lib/utils/speakers';

/** The voice of whoever raised the thread. */
export function threadVoice(thread: Thread): Voice {
	return raisedByAgent(thread) ? 'agent' : 'reader';
}
