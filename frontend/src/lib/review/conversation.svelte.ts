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

import { threadsIn } from '$lib/anchors/mentions';
import { cancelMessage, sendMessage } from '$lib/api/review-api';
import { PanelComposer } from '$lib/review/panel-composer.svelte';
import type { Composer, Thread, PanelTurn } from '$lib/types';
import { ANSWER_ID_PREFIX, EVENT_ID_PREFIX, IdSequence, MESSAGE_ID_PREFIX } from '$lib/utils/ids';
import { threadOnTheWire } from '$lib/api/thread-wire';
import { messageOf } from '$lib/utils/errors';
import { AGENT, READER, THE_REVIEW } from '$lib/utils/speakers';

/**
 * The message the agent is still working on.
 *
 * Only the last one: an older question answered out of order is the agent's
 * business, and two "working" lines in a conversation read as a fault.
 */
function workingOn(turns: PanelTurn[]): PanelTurn | undefined {
	const last = turns.findLast((turn) => turn.author === READER);
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
	// A message on its way: nothing more is sent until it is answered
	#sending = $state(false);
	// Why the last message did not go, until the next one is tried
	#failed = $state<string | null>(null);
	// The review's threads as they stand, which an answer may mention by their tokens
	readonly #threads: () => Thread[];

	/**
	 * @param said what was said here in an unsent review of the same thing
	 * @param composer the message being written there
	 * @param threads the review's threads as they stand
	 */
	constructor(said: PanelTurn[], composer: Composer, threads: () => Thread[]) {
		this.composer = new PanelComposer(composer);
		this.#threads = threads;
		this.#turns = $state.raw(said);
		this.#working = $derived(workingOn(this.#turns));
		// Past the highest id already handed out, so an answer cannot land under
		// a message that only shares its number
		const saidIds = said.map((turn) => turn.id);
		this.#messageIds.continuePast(saidIds);
		this.#answerIds.continuePast(saidIds);
		this.#eventIds.continuePast(saidIds);
	}

	get turns(): PanelTurn[] {
		return this.#turns;
	}

	/** The message the agent is still working on, if any. */
	get working(): PanelTurn | undefined {
		return this.#working;
	}

	/** Whether a message is on its way. */
	get sending(): boolean {
		return this.#sending;
	}

	/** Why the last message did not go, if it did not. */
	get failed(): string | null {
		return this.#failed;
	}

	/**
	 * Send the message being written, and go on reading; whether it went.
	 *
	 * The threads travel with the message rather than only their ids: they
	 * are unsent work, held in this browser, and the server has never seen
	 * them. Images are the other way round: the server already keeps them,
	 * so only their ids go. One message is on its way at a time, whoever
	 * draws the panel meanwhile; a failure is said, not thrown, and the words
	 * stay in the field to send again.
	 */
	async send(threads: Thread[]): Promise<boolean> {
		if (this.#sending) return false;
		this.#sending = true;
		this.#failed = null;
		const written = this.composer.text;
		const text = written.trim();
		const images = [...this.composer.attachments.images];
		const id = this.#messageIds.next();
		this.#say({
			id,
			author: READER,
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
			this.#failed = messageOf(error);
			return false;
		} finally {
			this.#sending = false;
		}
		this.composer.takeSent(written, images);
		return true;
	}

	/** Take what the agent said and put it under what it answers, if anything. */
	receive(messageId: string | null, text: string, files: string[]): void {
		this.#say({
			id: this.#answerIds.next(),
			author: AGENT,
			body: text,
			at: Date.now(),
			...(messageId === null ? {} : { answers: messageId }),
			files,
			// The threads its words mention by their tokens, as a message of the reader's points at them
			threads: threadsIn(text, this.#threads()).map((thread) => thread.id)
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
			author: THE_REVIEW,
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

	#markCancelled(messageId: string, cancelled: boolean): void {
		this.#turns = this.#turns.map((turn) => (turn.id === messageId ? { ...turn, cancelled } : turn));
	}
}
