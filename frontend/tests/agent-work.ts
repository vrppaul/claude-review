import type { AgentWork } from '$lib/types';

/** Work the server says is under way: for no message, nothing branched, unless given otherwise. */
export function work(given: Partial<AgentWork> = {}): AgentWork {
	return {
		message_id: null,
		text: 'reading the handler',
		files: [],
		steps: [],
		at: Date.now(),
		...given
	};
}
