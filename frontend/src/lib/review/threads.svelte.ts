/**
 * The threads of the review: what the reader wrote, what the agent raised,
 * and everything said in each since.
 *
 * They are unsent work and live only in this page until a round carries
 * them, so the draft keeps them across a reload, and the server is told
 * what the page holds for an agent that attaches later.
 */

import { askInThread, cancelMessage, followAnchors } from '$lib/api/review-api';
import { blockKey } from '$lib/anchors/story';
import type { ThreadOnLines } from '$lib/anchors/views';
import type { IssuedIds, KeptThreads } from '$lib/drafts/draft-shapes';
import type { CommentField } from '$lib/review/comment-field.svelte';
import type { CommentFields } from '$lib/review/comment-fields';
import { followedThreads } from '$lib/review/following';
import type { Rounds } from '$lib/review/rounds.svelte';
import { ThreadReading } from '$lib/review/thread-reading.svelte';
import { anchorWrittenOn, type ThreadOnBlock, withItsBlock, withItsLines } from '$lib/review/thread-places';
import { type CarriedThread, ThreadSending } from '$lib/review/thread-sending.svelte';
import { ThreadWriting } from '$lib/review/thread-writing.svelte';
import type {
	Anchor,
	CommentSeverity,
	FollowOutcome,
	HeldThread,
	NewComment,
	NewTurn,
	StoryBlock,
	Thread,
	ThreadDraft,
	Turn
} from '$lib/types';
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from '$lib/utils/ids';
import { threadOnTheWire } from '$lib/api/thread-wire';
import { AGENT, READER } from '$lib/utils/speakers';

/** When the agent last answered in a thread; 0 for a thread it never answered. */
function lastAnsweredAt(thread: Thread): number {
	return thread.turns.findLast((turn) => turn.author === AGENT)?.at ?? 0;
}

/**
 * Which question asking in a thread puts: the reader's reply when theirs is
 * the last word, and otherwise the thread itself, by its opening comment.
 * Decided here alone: the server finds what the id names, and asks nothing
 * else of it.
 */
function questionIdOf(thread: Thread): string {
	const last = thread.turns.at(-1);
	return last?.author === READER ? last.id : thread.id;
}

/** What a file with no threads on its lines holds. */
const NO_THREADS: readonly ThreadOnLines[] = [];

/** A comment field holding something not said yet, and what it is written on. */
export interface OpenField {
	field: CommentField;
	anchor: Anchor;
}

/** Whether a thread the review holds is as the agent raised it: nothing settled, and nothing said in it by the reader. */
function isAsRaised(held: HeldThread): boolean {
	return held.raised_by === AGENT && !held.resolved && held.turns.every((turn) => turn.author !== READER);
}

/**
 * A thread the review holds, as this page holds one. When it was written was
 * never told, nor which question an answer belongs to; the round it was
 * written in is no later than the first thing said in it, nor than now.
 */
function threadOfHeld(held: HeldThread, currentRound: number): Thread {
	return {
		id: held.thread_id,
		anchor: held.anchor,
		severity: held.severity,
		body: held.body,
		images: held.images,
		turns: held.turns.map(({ turn_id, author, body, round, images }) => ({ id: turn_id, author, body, round, images })),
		raised_by: held.raised_by,
		resolved: held.resolved,
		round: Math.min(currentRound, ...held.turns.map((turn) => turn.round))
	};
}

/** Words put into the review and asked about straight away: the thread they went into, and the asking. */
export interface SaidAndAsked {
	thread: string;
	/** Settled once the question is handed over; refused, it says why. */
	asked: Promise<void>;
}

export class Threads {
	/** How the page reads them: folded, unread, waiting on an answer. */
	readonly reading: ThreadReading;
	/** What is being written in them, and on lines that have none yet. */
	readonly writing: ThreadWriting;
	readonly #rounds: Rounds;
	#all = $state.raw<Thread[]>([]);
	// Which have gone out, in which round, and which the reader has changed since
	readonly #sending: ThreadSending;
	readonly #commentIds = new IdSequence(COMMENT_ID_PREFIX);
	readonly #turnIds = new IdSequence(TURN_ID_PREFIX);
	readonly #onLines = $derived(this.#all.flatMap(withItsLines));
	// By the file they hang on, so a file asks for its own without a scan
	readonly #byFile = $derived(Map.groupBy(this.#onLines, ({ lines }) => lines.file));
	readonly #onTheStory = $derived(this.#all.flatMap(withItsBlock));
	// Those on the story's words, by the block they hang on, so a block asks for its own without a scan
	readonly #byBlock = $derived(Map.groupBy(this.#onTheStory, ({ block }) => block));
	readonly #unread = $derived(this.#all.filter((thread) => this.reading.isUnread(thread.id)));
	readonly #unsent = $derived(this.#all.filter((thread) => this.#sending.roundOf(thread.id) === undefined));
	readonly #onTheWire = $derived(this.#all.map(threadOnTheWire));
	readonly #answered = $derived(
		this.#all
			.filter((thread) => thread.turns.length > 0)
			.sort((first, second) => lastAnsweredAt(second) - lastAnsweredAt(first))
	);

	/**
	 * @param rounds the round each thread and turn is stamped with
	 * @param kept the threads of an unsent review of the same thing, picked up where it stopped
	 * @param fieldEvents where what happens to the fields they are written in is told
	 */
	constructor(rounds: Rounds, kept: KeptThreads, fieldEvents: CommentFields) {
		this.#rounds = rounds;
		this.reading = new ThreadReading(kept.read);
		this.writing = new ThreadWriting(kept.writing, fieldEvents, kept.threads);
		this.#sending = new ThreadSending(kept.sent);
		this.#pickUp(kept);
	}

	get all(): Thread[] {
		return this.#all;
	}

	get count(): number {
		return this.#all.length;
	}

	/** Threads carrying an answer nobody has looked at. */
	get unread(): Thread[] {
		return this.#unread;
	}

	/** Threads the answering side has not been told about yet. */
	get unsent(): Thread[] {
		return this.#unsent;
	}

	/** Every thread as the other side is told about it. */
	get onTheWire(): ThreadDraft[] {
		return this.#onTheWire;
	}

	/** Threads that have been discussed, newest answer first. */
	get answered(): readonly Thread[] {
		return this.#answered;
	}

	/** Every thread on lines of a file, with its lines. */
	get onLines(): readonly ThreadOnLines[] {
		return this.#onLines;
	}

	/** The threads hanging on lines of one file, each with its lines. */
	onLinesOf(path: string): readonly ThreadOnLines[] {
		return this.#byFile.get(path) ?? NO_THREADS;
	}

	/** Every thread on a block of the story's words, in the order they were written, each with its block. */
	get onTheStory(): readonly ThreadOnBlock[] {
		return this.#onTheStory;
	}

	/** The threads hanging on a block of the story's words, in the order they were written. */
	onBlock(block: StoryBlock): Thread[] {
		return (this.#byBlock.get(blockKey(block)) ?? []).map(({ thread }) => thread);
	}

	/** The round every thread sent so far went out in, by thread, as the draft keeps them. */
	get sentRounds(): Record<string, number> {
		return this.#sending.rounds;
	}

	/** How many thread and turn ids have been handed out, deleted ones included. */
	get issued(): IssuedIds {
		return { comments: this.#commentIds.issued, turns: this.#turnIds.issued };
	}

	/** Which round a thread went out in, or nothing if it has not yet. */
	sentInRound(id: string): number | undefined {
		return this.#sending.roundOf(id);
	}

	add({ anchor, body, severity, images }: NewComment): string {
		const thread: Thread = {
			id: this.#commentIds.next(),
			anchor,
			severity,
			body,
			images,
			turns: [],
			raised_by: READER,
			resolved: false,
			round: this.#rounds.current,
			at: Date.now()
		};
		this.#all = [...this.#all, thread];
		return thread.id;
	}

	/**
	 * Take a thread the agent raised and put it on the diff; whether it was
	 * new. One the page holds already — taken in with the review's threads
	 * as it opened — is not raised twice.
	 *
	 * It arrives already sent: the reader has not written it, so it must not
	 * swell "unsent" or travel back to the side that wrote it. The moment
	 * they answer or edit it, it stops being sent — as any thread does — and
	 * goes with the next round, so the reply arrives with what it replies to.
	 */
	raise(id: string, anchor: Anchor, body: string, severity: CommentSeverity): boolean {
		if (this.#all.some((held) => held.id === id)) return false;
		const thread: Thread = {
			id,
			anchor,
			severity,
			body,
			images: [],
			turns: [],
			raised_by: AGENT,
			resolved: false,
			round: this.#rounds.current,
			at: Date.now()
		};
		this.#all = [...this.#all, thread];
		this.reading.markUnread(id);
		this.#sending.arrivedSent(id, this.#rounds.current);
		return true;
	}

	/**
	 * Take as this page's own the threads the review holds, for a page that
	 * opened with no draft of the review: another browser, a private window.
	 *
	 * Which of them went out with a round only the page that sent them
	 * knew, so each is taken as not sent yet — sent twice costs the agent a
	 * second look, never sent costs the reader the comment — but for one
	 * still as the agent raised it, taken as a raised thread arrives. Ids go
	 * on past theirs, so nothing written here takes one of them.
	 */
	adopt(held: HeldThread[]): void {
		this.#all = [...this.#all, ...held.map((thread) => threadOfHeld(thread, this.#rounds.current))];
		for (const thread of held.filter(isAsRaised)) this.#sending.arrivedSent(thread.thread_id, this.#rounds.current);
		this.#commentIds.continuePast(held.map((thread) => thread.thread_id));
		this.#turnIds.continuePast(held.flatMap((thread) => thread.turns.map((turn) => turn.turn_id)));
	}

	update(id: string, body: string, severity: CommentSeverity, images: string[]): void {
		this.#sending.changedByReader(id);
		this.#replace(id, (thread) => ({ ...thread, body, severity, images }));
	}

	remove(id: string): void {
		this.#sending.changedByReader(id);
		this.reading.forget(id);
		this.writing.forget(id);
		this.#all = this.#all.filter((thread) => thread.id !== id);
	}

	/**
	 * Put what a field holds into the review, and close the field: a comment
	 * on lines or on a block of the story becomes a thread, a reply a turn of
	 * its thread, an edit the thread's opening comment. Returns the thread it
	 * went into.
	 */
	say(field: CommentField): string {
		const thread = this.#writeOut(field, field.severity);
		this.writing.added(field);
		return thread;
	}

	/**
	 * Put what a field holds into the review as a question, and hand its
	 * thread straight to whoever is answering. A question by definition:
	 * asking and then leaving the comment marked as a note would say two
	 * different things about the same words.
	 */
	sayAndAsk(field: CommentField): SaidAndAsked {
		const thread = this.#writeOut(field, 'question');
		this.writing.asked(field);
		return { thread, asked: this.ask(thread) };
	}

	/**
	 * The fields holding something not said yet: a comment started on lines, a
	 * reply, an edit that changes what its thread says. What a send takes
	 * along, and the pane it goes from lists.
	 */
	get open(): OpenField[] {
		return this.writing.fields.filter((field) => field.sayable).flatMap((field) => this.#openOn(field));
	}

	/**
	 * Put into the review what every open field holds, as a send does before it
	 * goes: a pending comment goes with the review, as on GitHub, rather than
	 * being left behind by a round or forgotten with the draft by the end.
	 */
	sayOpen(): void {
		for (const { field } of this.open) this.say(field);
	}

	/** Add what someone said to a thread. */
	addTurn(id: string, { author, body, images }: NewTurn): void {
		const turn: Turn = {
			id: this.#turnIds.next(),
			author,
			body,
			round: this.#rounds.current,
			at: Date.now(),
			images
		};
		this.#sending.changedByReader(id);
		this.#replace(id, (thread) => ({
			...thread,
			turns: [...thread.turns, turn]
		}));
	}

	/**
	 * Hand a thread over to whoever is answering, and carry on reading.
	 *
	 * The whole thread goes, as it stands, and the server reads the question
	 * out of it: the reply just written, or the comment that opened it. It
	 * goes with an id, so an answer to the second question does not arrive as
	 * an answer to the third — and with everything said, so it does not have
	 * to guess what the thread was about.
	 */
	async ask(id: string): Promise<void> {
		const thread = this.#all.find((candidate) => candidate.id === id);
		if (!thread) return;

		const questionId = questionIdOf(thread);
		this.reading.asked(id, questionId);
		try {
			await askInThread({
				question_id: questionId,
				thread: threadOnTheWire(thread)
			});
		} catch (error) {
			this.reading.settled(id, questionId);
			throw error;
		}
	}

	/**
	 * Take back a question still waited on, as a message in the panel is
	 * taken back: whoever answers is asked to drop it — a request, not a kill
	 * — and once that is heard the thread waits for it no more. An answer the
	 * agent writes all the same still lands in the thread.
	 */
	async takeBack(threadId: string, questionId: string): Promise<void> {
		await cancelMessage({ message_id: questionId });
		this.reading.tookBack(threadId, questionId);
	}

	/**
	 * Take an answer that came back and put it under the question it answers,
	 * as the reading tells which. Says whether there was a thread to put it in.
	 */
	receiveReply(id: string, text: string, questionId: string | null): boolean {
		if (!this.#all.some((thread) => thread.id === id)) return false;

		const answers = this.reading.settleAnswer(id, questionId);
		const turn: Turn = {
			id: this.#turnIds.next(),
			author: AGENT,
			body: text,
			round: this.#rounds.current,
			at: Date.now(),
			images: [],
			...(answers === undefined ? {} : { answers })
		};
		// Not marked unsent: the answer came from the side that reads the
		// rounds, so sending it back would only repeat what they wrote
		this.#replace(id, (answered) => ({
			...answered,
			turns: [...answered.turns, turn]
		}));
		this.reading.answerArrived(id, turn.id);
		return true;
	}

	/** Settle a thread, which folds it away, or open it again. */
	setResolved(id: string, resolved: boolean): void {
		this.#sending.changedByReader(id);
		this.#replace(id, (thread) => ({ ...thread, resolved }));
		if (resolved) this.reading.setFolded(id, true);
	}

	/** The threads a round about to go carries, as `markSent` is handed them back once it has gone. */
	carry(threads: readonly Thread[]): CarriedThread[] {
		return this.#sending.carry(threads);
	}

	/**
	 * Note that the threads a round carried went out in it. One the reader
	 * changed since, while the round was on its way, is a thread the round did
	 * not carry as it is now, and goes with the next; one the agent answered
	 * meanwhile, or the diff moved, still went as the reader wrote it.
	 */
	markSent(carried: readonly CarriedThread[], round: number): void {
		this.#sending.markSent(carried, round);
	}

	/**
	 * Move every thread onto the diff as it now stands.
	 *
	 * Called after a round is answered and the diff retaken. The server holds
	 * that diff, so it says where each thread now hangs: one whose lines
	 * survived follows them, and one whose lines are gone is marked rather
	 * than left pointing at a line that has become something else.
	 *
	 * Says how many did each, because that is what the reader stands to lose
	 * and the only part of a retake they cannot see at a glance.
	 */
	async follow(): Promise<FollowOutcome> {
		const asked = this.#all;
		const { anchors } = await followAnchors({ anchors: asked.map((thread) => thread.anchor) });
		const { threads, outcome } = followedThreads(asked, anchors, this.#all);
		this.#all = threads;
		return outcome;
	}

	/** Pick up the threads of an unsent review of the same thing, kept before a reload. */
	#pickUp(kept: KeptThreads): void {
		this.#all = kept.threads;
		this.#commentIds.continueFrom(kept.issued.comments);
		this.#turnIds.continueFrom(kept.issued.turns);
	}

	/** Write out what a field holds, meant as this; the thread it went into. */
	#writeOut(field: CommentField, severity: CommentSeverity): string {
		const body = field.text.trim();
		const images = [...field.attachments.images];
		const { at } = field;
		switch (at.kind) {
			case 'new':
			case 'story':
				return this.add({ anchor: anchorWrittenOn(at), body, severity, images });
			case 'reply':
				this.addTurn(at.thread, { author: READER, body, images });
				return at.thread;
			case 'edit':
				this.update(at.thread, body, severity, images);
				return at.thread;
		}
	}

	/** What an open field is written on, as one, or none when it would say nothing new. */
	#openOn(field: CommentField): OpenField[] {
		const { at } = field;
		if (at.kind === 'new' || at.kind === 'story') return [{ field, anchor: anchorWrittenOn(at) }];
		const thread = this.#all.find((candidate) => candidate.id === at.thread);
		// An edit holding nothing the reader put in it says what its thread says already
		if (!thread || (at.kind === 'edit' && !field.holdsWork)) return [];
		return [{ field, anchor: thread.anchor }];
	}

	#replace(id: string, change: (thread: Thread) => Thread): void {
		this.#all = this.#all.map((thread) => (thread.id === id ? change(thread) : thread));
	}
}
