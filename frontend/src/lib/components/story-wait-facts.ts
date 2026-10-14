/**
 * What a reader waiting for a story is told of it, fact by fact: what has
 * happened, each with the moment it did, and last the one thing still
 * waited for, with how long that has taken. A wait with nothing to read on
 * it looks like a hang; these are read off the asking as the review says it
 * stands, so each line is something that happened.
 *
 * The time now is read from the review's clock, and only by a fact that
 * counts from a moment: a request that has not landed has no moment to
 * count from, and keeps no clock running.
 */

import type { Clock } from '$lib/review/clock.svelte';
import type { StoryWait } from '$lib/review/story-wait';
import type { StoryAsking } from '$lib/types';
import { clockTimeToTheSecond, timeWaited } from '$lib/utils/time';

/** A wait a story is on its way in: its request not landed yet, or landed and not stopped. */
export type StoryOnItsWay = Extract<StoryWait, { kind: 'unasked' | 'writing' }>;

/** One line of what the reader is told of a story on its way. */
export interface WaitFact {
	/** Whether it has happened, or is what is waited for now. */
	state: 'happened' | 'awaited';
	says: string;
	/** When it happened, or how long it has been waited for; nothing where there is no moment to count from. */
	when: string | null;
}

// What a line says: of the request, before the review has said anything of it and once it holds it; of
// the agent, until it takes the request and once it has; and of the story waited for from then on
const ASKING = 'Asking the agent for a story';
const ASKED = 'Asked the agent for a story';
const TAKING_AWAITED = 'Waiting for the agent to take the request';
const TAKEN = 'The agent took the request';
const STORY_AWAITED = 'Waiting for the story';

// The request is on its way to the review, which has said nothing of it yet
const BEING_ASKED: WaitFact = { state: 'awaited', says: ASKING, when: null };

function happened(says: string, at: number): WaitFact {
	return { state: 'happened', says, when: clockTimeToTheSecond(at) };
}

function awaited(says: string, since: number, clock: Clock): WaitFact {
	return { state: 'awaited', says, when: timeWaited(since, clock.now) };
}

/**
 * The facts of a story asked for: that it was, then whether an agent took
 * the request. Until one has, the taking is what is waited for; once one
 * has, the story is, counted from the moment it was taken.
 */
function factsOfAsking(asking: StoryAsking, clock: Clock): WaitFact[] {
	const asked = happened(ASKED, asking.asked_at);
	if (asking.taken_at === null) return [asked, awaited(TAKING_AWAITED, asking.asked_at, clock)];
	return [asked, happened(TAKEN, asking.taken_at), awaited(STORY_AWAITED, asking.taken_at, clock)];
}

/** What the reader is told of a story on its way, in the order it happened: the last line is what is waited for. */
export function factsOnTheWay(wait: StoryOnItsWay, clock: Clock): WaitFact[] {
	return wait.kind === 'writing' ? factsOfAsking(wait.asking, clock) : [BEING_ASKED];
}
