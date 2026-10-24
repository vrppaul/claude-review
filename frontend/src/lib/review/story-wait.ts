/**
 * What a reader with no current story to read is waiting on, said as one of
 * four kinds: whoever acts on the wait, or draws it, asks which, and never
 * weighs the facts itself.
 *
 * The page holds two facts of it and no third: how the asking for a story
 * stands, as the review says, and whether an agent is attached. The kind is
 * worked out from them whenever it is read and kept nowhere, so nothing on
 * the page can go on saying a story is on its way once the facts say
 * otherwise.
 */

import type { StoryAsking } from '$lib/types';

/**
 * What the reader is waiting on while the review holds no story that is
 * current: none, or one a round moved the code on under.
 *
 * `unasked`: nobody asked for one, or the request has not landed yet.
 * `writing`: one was asked for and is on its way: an agent took the
 * request, or one is attached and will; it carries the asking, whose
 * moments say how long the reader has waited.
 * `nobody-attached`: one was asked for, and no agent is there to take the
 * request.
 * `stopped`: the reader stopped the one they asked for.
 */
export type StoryWait =
	| { kind: 'unasked' }
	| { kind: 'writing'; asking: StoryAsking }
	| { kind: 'nobody-attached' }
	| { kind: 'stopped' };

const UNASKED: StoryWait = { kind: 'unasked' };
const NOBODY_ATTACHED: StoryWait = { kind: 'nobody-attached' };
const STOPPED: StoryWait = { kind: 'stopped' };

// Whether the reader asked for a story in each kind of wait: it is on its way, waits for an agent, or they stopped it
const ASKED_FOR: Record<StoryWait['kind'], boolean> = {
	unasked: false,
	writing: true,
	'nobody-attached': true,
	stopped: true
};

/**
 * What a reader with no current story held is waiting on. A request an
 * agent took is being written whoever is attached now: an agent that went
 * quiet is judged by how long the reader has waited, never guessed at here.
 */
export function waitOf(asking: StoryAsking | null, agentAttached: boolean): StoryWait {
	if (asking === null) return UNASKED;
	if (asking.stopped) return STOPPED;
	if (asking.taken_at !== null || agentAttached) return { kind: 'writing', asking };
	return NOBODY_ATTACHED;
}

/**
 * Whether the reader asked for a story, which has not been told since: on
 * its way, waiting for an agent, or stopped by them. With a current story
 * held there is no wait at all.
 */
export function isAskedFor(wait: StoryWait | null): boolean {
	return wait !== null && ASKED_FOR[wait.kind];
}
