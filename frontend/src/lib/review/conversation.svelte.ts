/**
 * The conversation with the agent that is answering this review.
 *
 * A thread is about one line. This is about everything else — the plan, the
 * tests, a file nobody commented on — and it reaches the same agent: the
 * process driving `claude-review wait`, which wrote the change and has the
 * repository in front of it.
 *
 * Nothing typed here waits for a round. There is one button, because "add
 * to review" has no meaning outside a thread.
 */

import { cancelMessage, sendMessage } from '$lib/api/review-api';
import { PanelComposer } from '$lib/review/panel-composer.svelte';
import type { Draft } from '$lib/drafts/draft-shapes';
import type { Thread, PanelTurn } from '$lib/types';
import { ANSWER_ID_PREFIX, EVENT_ID_PREFIX, IdSequence, MESSAGE_ID_PREFIX } from '$lib/utils/ids';
import { threadOnTheWire } from '$lib/api/thread-wire';

/**
 * The message the agent is still working on.
 *
 * Only the last one: an older question answered out of order is the agent's
 * business, and two "working" lines in a conversation read as a fault.
 */
function workingOn(turns: PanelTurn[]): PanelTurn | undefined {
	const last = turns.findLast((turn) => turn.author === 'reader');
	if (!last || last.cancelled) return undefined;
	return turns.some((turn) => turn.answers === last.id) ? undefined : last;
}

export class Conversation {
	/** The message being written. */
	readonly composer: PanelComposer;
	#turns: PanelTurn[];
	readonly #messageIds = new IdSequence(MESSAGE_ID_PREFIX);
	readonly #answerIds = new IdSequence(ANSWER_ID_PREFIX);
	readonly #eventIds = new IdSequence(EVENT_ID_PREFIX);
	readonly #working: PanelTurn | undefined;

	/** @param draft an unsent review of the same thing, with what was said here */
	constructor(draft: Draft | null) {
		this.composer = new PanelComposer(draft);
		this.#turns = $state([]);
		this.#working = $derived(workingOn(this.#turns));
		if (draft !== null) this.#pickUp(draft.panel);
	}

	get turns(): PanelTurn[] {
		return this.#turns;
	}

	/** Take in what another tab on the same review has said here. */
	adopt(draft: Draft): void {
		this.#pickUp(draft.panel);
		this.composer.adopt(draft);
	}

	/** The message the agent is still working on, if any. */
	get working(): PanelTurn | undefined {
		return this.#working;
	}

	/**
	 * Send the message being written, and go on reading.
	 *
	 * The threads travel with the message rather than only their ids: they
	 * are unsent work, held in this browser, and the server has never seen
	 * them. Images are the other way round: the server already keeps them,
	 * so only their ids go.
	 */
	async send(threads: Thread[]): Promise<void> {
		const written = this.composer.text;
		const text = written.trim();
		const images = [...this.composer.attachments.images];
		const id = this.#messageIds.next();
		this.#say({
			id,
			author: 'reader',
			body: text,
			at: Date.now(),
			threads: threads.map((thread) => thread.id),
			images
		});

		try {
			await sendMessage({
				message_id: id,
				body: text,
				threads: threads.map(threadOnTheWire),
				images
			});
		} catch (error) {
			// Never reached the agent, so it is taken off the conversation
			this.#turns = this.#turns.filter((turn) => turn.id !== id);
			throw error;
		}
		this.composer.takeSent(written, images);
	}

	/** Take what the agent said and put it under what it answers, if anything. */
	receive(messageId: string | null, text: string, files: string[]): void {
		this.#say({
			id: this.#answerIds.next(),
			author: 'author',
			body: text,
			at: Date.now(),
			...(messageId === null ? {} : { answers: messageId }),
			files
		});
	}

	/**
	 * Note something the review itself did, between what was said about it.
	 *
	 * A retaken diff is not a turn — nobody said it — but it happened in the
	 * middle of the conversation, and an answer written before it was written
	 * about different code.
	 */
	note(body: string, threads: string[] = []): void {
		this.#say({
			id: this.#eventIds.next(),
			author: 'event',
			body,
			at: Date.now(),
			threads
		});
	}

	/**
	 * Take a message back before it is answered.
	 *
	 * A request, not a kill: the agent is in another process and decides what
	 * to do about it. The panel stops waiting either way, because the reader
	 * has said they are no longer interested.
	 */
	async cancel(messageId: string): Promise<void> {
		this.#markCancelled(messageId, true);
		try {
			await cancelMessage({ message_id: messageId });
		} catch (error) {
			// Never heard, so the agent is still on it and the panel still waits
			this.#markCancelled(messageId, false);
			throw error;
		}
	}

	#say(turn: PanelTurn): void {
		this.#turns = [...this.#turns, turn];
	}

	#pickUp(said: PanelTurn[]): void {
		this.#turns = said;
		// Past the highest id already handed out, so an answer cannot land under
		// a message that only shares its number
		const saidIds = said.map((turn) => turn.id);
		this.#messageIds.continuePast(saidIds);
		this.#answerIds.continuePast(saidIds);
		this.#eventIds.continuePast(saidIds);
	}

	#markCancelled(messageId: string, cancelled: boolean): void {
		this.#turns = this.#turns.map((turn) => (turn.id === messageId ? { ...turn, cancelled } : turn));
	}
}
