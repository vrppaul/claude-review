/**
 * The conversation with the agent that is answering this review.
 *
 * A thread is about the lines it hangs on. This is about everything else — the plan, the
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
import type { ChatPush, Composer, Thread, PanelTurn, SaidInPanel } from '$lib/types';
import { EVENT_ID_PREFIX, IdSequence, MESSAGE_ID_PREFIX } from '$lib/utils/ids';
import { threadOnTheWire } from '$lib/api/thread-wire';
import { messageOf } from '$lib/utils/errors';
import { AGENT, READER, THE_REVIEW } from '$lib/utils/speakers';

// Why a message handed over while another is on its way does not go
const ONE_AT_A_TIME = 'Another message is on its way to the agent: try again once it has gone.';

/** What the agent said, as it is pushed and as the review holds it: under its id, answering a message or not. */
type AgentWords = Pick<ChatPush, 'said_id' | 'message_id' | 'body' | 'files'>;

/** The agent's words as a turn: under what they answer, with their files and the threads they mention by token. */
function agentTurn(words: AgentWords, at: number, threads: Thread[]): PanelTurn {
	return {
		id: words.said_id,
		author: AGENT,
		body: words.body,
		at,
		...(words.message_id === null ? {} : { answers: words.message_id }),
		files: words.files,
		// The threads its words mention by their tokens, as a message of the reader's points at them
		threads: threadsIn(words.body, threads).map((thread) => thread.id)
	};
}

/** Something the review holds as said, as the turn the page drew when it was said. */
function turnOfHeld(said: SaidInPanel, threads: Thread[]): PanelTurn {
	if (said.author === AGENT) return agentTurn(said, said.at, threads);
	return {
		id: said.said_id,
		author: READER,
		body: said.body,
		at: said.at,
		threads: said.threads,
		images: said.images,
		...(said.taken_back_at === null ? {} : { takenBackAt: said.taken_back_at })
	};
}

/**
 * What the panel opens on. What the review holds is drawn as it holds it —
 * it heard every part, from every window — and the draft adds only what the
 * review does not hold: the review's own notes, and what was said before it
 * last started. All of it in the order it came.
 */
function openingTurns(held: PanelTurn[], kept: PanelTurn[]): PanelTurn[] {
	const heldIds = new Set(held.map((turn) => turn.id));
	const keptOnly = kept.filter((turn) => !heldIds.has(turn.id));
	return [...held, ...keptOnly].sort((earlier, later) => earlier.at - later.at);
}

/**
 * The message the agent is still working on.
 *
 * Only the last one: an older question answered out of order is the agent's
 * business, and two "working" lines in a conversation read as a fault.
 */
function workingOn(turns: PanelTurn[]): PanelTurn | undefined {
	const last = turns.findLast((turn) => turn.author === READER);
	if (!last || last.takenBackAt !== undefined) return undefined;
	return turns.some((turn) => turn.answers === last.id) ? undefined : last;
}

export class Conversation {
	/** The message being written. */
	readonly composer: PanelComposer;
	#turns: PanelTurn[];
	readonly #messageIds = new IdSequence(MESSAGE_ID_PREFIX);
	readonly #eventIds = new IdSequence(EVENT_ID_PREFIX);
	readonly #working: PanelTurn | undefined;
	// A message on its way: nothing more is sent until it is answered
	#sending = $state(false);
	// Why the last message did not go, until the next one is tried
	#failed = $state<string | null>(null);
	// The review's threads as they stand, which an answer may mention by their tokens
	readonly #threads: () => Thread[];

	/**
	 * @param kept what was said here in an unsent review of the same thing
	 * @param held what the review holds as said, from whatever window
	 * @param composer the message being written there
	 * @param threads the review's threads as they stand
	 */
	constructor(kept: PanelTurn[], held: SaidInPanel[], composer: Composer, threads: () => Thread[]) {
		this.composer = new PanelComposer(composer);
		this.#threads = threads;
		const threadsHeld = threads();
		const said = openingTurns(
			held.map((entry) => turnOfHeld(entry, threadsHeld)),
			kept
		);
		this.#turns = $state.raw(said);
		this.#working = $derived(workingOn(this.#turns));
		// Past the highest id already handed out, here or in another window, so
		// an answer cannot land under a message that only shares its number
		const saidIds = said.map((turn) => turn.id);
		this.#messageIds.continuePast(saidIds);
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
		this.#failed = null;
		const written = this.composer.text;
		const images = [...this.composer.attachments.images];
		try {
			await this.#deliver(written.trim(), threads, images);
		} catch (error) {
			this.#failed = messageOf(error);
			return false;
		}
		this.composer.takeSent(written, images);
		return true;
	}

	/**
	 * Hand the agent words written elsewhere than the panel's field — a
	 * reader's feedback on the review itself — as a message of theirs, said
	 * in the panel and answered there. It throws where they did not go, for
	 * whoever handed them to say why.
	 */
	async hand(words: string): Promise<void> {
		await this.#deliver(words, [], []);
	}

	/**
	 * Say a message of the reader's in the panel and send it, one at a time; one that never reached the agent is
	 * taken off.
	 */
	async #deliver(body: string, threads: Thread[], images: string[]): Promise<void> {
		if (this.#sending) throw new Error(ONE_AT_A_TIME);
		this.#sending = true;
		const id = this.#messageIds.next();
		this.#say({
			id,
			author: READER,
			body,
			at: Date.now(),
			threads: threads.map((thread) => thread.id),
			images
		});
		try {
			await sendMessage({ message_id: id, body, threads: threads.map(threadOnTheWire), images });
		} catch (error) {
			this.#turns = this.#turns.filter((turn) => turn.id !== id);
			throw error;
		} finally {
			this.#sending = false;
		}
	}

	/**
	 * Take what the agent said and put it under what it answers, if anything;
	 * whether it was new. Words the page read from the review as it opened are
	 * in the panel already, and their push says them again.
	 */
	receive(words: AgentWords): boolean {
		if (this.#turns.some((turn) => turn.id === words.said_id)) return false;
		this.#say(agentTurn(words, Date.now(), this.#threads()));
		return true;
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
	 * Take a message back before it is answered, as a thread takes back its
	 * question: once the review has heard it, the panel waits for it no more.
	 *
	 * A request, not a kill: the agent is in another process and decides what
	 * to do about it. Where the review refuses — it never heard, or the answer
	 * crossed the request on its way — the agent is still on it, or done, and
	 * nothing is marked: the failure is said where the reader asked.
	 */
	async cancel(messageId: string): Promise<void> {
		await cancelMessage({ message_id: messageId });
		this.#markTakenBack(messageId, Date.now());
	}

	#say(turn: PanelTurn): void {
		this.#turns = [...this.#turns, turn];
	}

	#markTakenBack(messageId: string, takenBackAt: number): void {
		this.#turns = this.#turns.map((turn) => (turn.id === messageId ? { ...turn, takenBackAt } : turn));
	}
}
