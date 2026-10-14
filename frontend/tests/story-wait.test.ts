import { describe, it, expect } from 'vitest';
import fastCheck from 'fast-check';
import { waitOf } from '$lib/review/story-wait';
import { ASKED, ASKED_AT, STOPPED, TAKEN } from './story';

/** A page where an agent is attached to the review, and one where nobody is. */
const AN_AGENT_ATTACHED = true;
const NOBODY_ATTACHED = false;

describe('what a reader with no story held is waiting on', () => {
	it('is a story not asked for yet, while the review says nothing of an asking', () => {
		expect(waitOf(null, NOBODY_ATTACHED)).toEqual({ kind: 'unasked' });
	});

	it('is a story being written once an agent took the request, though none is attached now', () => {
		expect(waitOf(TAKEN, NOBODY_ATTACHED)).toEqual({ kind: 'writing', asking: TAKEN });
	});

	it('is a story being written while an agent is attached, before it has taken the request', () => {
		expect(waitOf(ASKED, AN_AGENT_ATTACHED)).toEqual({ kind: 'writing', asking: ASKED });
	});

	it('is an agent to attach, while the request waits and nobody is there to take it', () => {
		expect(waitOf(ASKED, NOBODY_ATTACHED)).toEqual({ kind: 'nobody-attached' });
	});

	it('is nothing more once the reader stopped the story', () => {
		expect(waitOf(STOPPED, NOBODY_ATTACHED)).toEqual({ kind: 'stopped' });
	});

	it('is stopped whoever is attached, and whether or not an agent had taken the request', () => {
		fastCheck.assert(
			fastCheck.property(fastCheck.boolean(), fastCheck.option(fastCheck.nat(), { nil: null }), (attached, takenAt) => {
				const stopped = { asked_at: ASKED_AT, taken_at: takenAt, stopped: true };

				expect(waitOf(stopped, attached)).toEqual({ kind: 'stopped' });
			})
		);
	});
});
