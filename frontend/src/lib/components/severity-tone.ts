/**
 * What a thread asks for, as its tag says it: the same on the thread's card
 * and in the list a round is sent from. Only what differs from a note is
 * said, and weighted by it: a question wants an answer, a blocker has to be
 * dealt with.
 */

import type { Thread } from '$lib/types';
import type { TagTone } from '$lib/ui/tag';
import { raisedByAgent } from '$lib/utils/speakers';

/** The tone of the tag a thread says what it asks for by: a question is asked in the colour of whoever wrote it. */
export function severityTone(thread: Thread): TagTone {
	if (thread.severity === 'blocker') return 'blocking';
	return raisedByAgent(thread) ? 'agent' : 'reader';
}
