/**
 * One review, opened: what it is, the diff on screen, the threads written
 * on it, the conversation beside it, and the reader's way of reading it.
 *
 * Built only once the review is known and its first diff has arrived, so
 * nothing in it has a "not loaded yet" to be asked about. Each part owns its
 * own state; what spans parts — whitespace retaking the diff, a retake
 * narrowing to what changed — is done here.
 */

import { Guide } from '$lib/guide/guide.svelte';
import type { PageLayout } from '$lib/reader/page-layout.svelte';
import type { ReplySound } from '$lib/reader/reply-sound';
import type { Settings } from '$lib/reader/settings.svelte';
import { Answerer } from '$lib/review/answerer.svelte';
import { CommentFields } from '$lib/review/comment-fields';
import { Conversation } from '$lib/review/conversation.svelte';
import { FileSections } from '$lib/dom/file-sections';
import { LastRetake } from '$lib/review/last-retake.svelte';
import { diffNotTakenNote } from '$lib/review/panel-notes';
import { ReadingProgress } from '$lib/review/reading-progress.svelte';
import { ReviewDiff } from '$lib/review/review-diff.svelte';
import { Rounds } from '$lib/review/rounds.svelte';
import { Submission } from '$lib/review/submission.svelte';
import { Telling } from '$lib/review/telling.svelte';
import { ThreadNavigator } from '$lib/review/thread-navigator';
import { Threads } from '$lib/review/threads.svelte';
import type {
	ChangesSince,
	DiffResponse,
	FollowOutcome,
	ReviewMode,
	ReviewResponse,
	SendLimits,
	SessionHello
} from '$lib/types';
import { DRAFT_SHAPE, type Draft, emptyDraft } from '$lib/drafts/draft-shapes';
import { diffCharacters, threadCharacters, tokensOf } from '$lib/review/weight';

/** What a review opens on: what the server says it is, its first diff, and any unsent draft. */
export interface Opening {
	facts: ReviewResponse;
	firstDiff: DiffResponse;
	draft: Draft | null;
}

/** Whoever carries what the page holds to the server. */
export interface Greeter {
	greet(hello: SessionHello): void;
}

/** What belongs to the reader rather than to the review, and outlives it. */
export interface ReaderParts {
	settings: Settings;
	layout: PageLayout;
	sound: ReplySound;
}

export class Review {
	/** What is under review — which repository, and against what. */
	readonly title: string;
	readonly mode: ReviewMode;
	/** What the server takes: pasted images, and the lines one comment covers. */
	readonly limits: SendLimits;

	readonly settings: Settings;
	readonly layout: PageLayout;
	readonly sound: ReplySound;

	readonly rounds: Rounds;
	/** How far the server's telling has got for this page. */
	readonly telling: Telling;
	readonly answerer: Answerer;
	readonly diff: ReviewDiff;
	readonly reading = new ReadingProgress();
	readonly lastRetake = new LastRetake();
	readonly threads: Threads;
	readonly submission: Submission;
	readonly conversation: Conversation;
	readonly guide: Guide;
	readonly sections = new FileSections();
	readonly navigator: ThreadNavigator;
	readonly commentFields = new CommentFields();

	// How many threads came back from the draft, so the reader is told rather
	// than left to wonder where they came from; zero once they have seen it
	#restoredCount: number;
	// What handing the diff on screen over costs, in characters: counted once
	// a diff, not again whenever a thread changes
	readonly #diffCharacters: number;
	// What handing this review over costs, as far as this side can tell
	readonly #weight: number;
	// What the page tells the server it holds: the round it has reached, and
	// the threads, which are unsent work and live only here
	readonly #hello: SessionHello;
	// The unsent review as a draft keeps it; none once the review is over
	readonly #draft: Draft | null;
	// The retake being taken in, so the next waits for it
	#retaking: Promise<unknown> = Promise.resolve();

	constructor({ facts, firstDiff, draft }: Opening, reader: ReaderParts) {
		this.title = facts.title;
		this.mode = facts.mode;
		this.limits = facts.limits;
		this.settings = reader.settings;
		this.layout = reader.layout;
		this.sound = reader.sound;

		// What the review picks up: the draft it opened from, or nothing yet
		const kept = draft ?? emptyDraft(facts.title);
		this.rounds = new Rounds(facts.round);
		this.telling = new Telling({ instance: facts.instance, sequence: facts.sequence }, kept.told);
		this.answerer = new Answerer(facts.answerer_attached, facts.agent, facts.work);
		this.diff = new ReviewDiff(firstDiff, () => this.settings.current.ignore_whitespace);
		this.threads = new Threads(this.rounds, kept, this.commentFields);
		this.submission = new Submission(this.threads, this.rounds, kept.reviewBody);
		this.conversation = new Conversation(kept.panel, kept.composer);
		this.guide = new Guide(this.answerer, facts.release);
		this.navigator = new ThreadNavigator(this.threads, this.reading, this.sections);
		this.#restoredCount = $state(draft === null ? 0 : this.threads.count);
		this.#diffCharacters = $derived(diffCharacters(this.diff.files));
		this.#weight = $derived(tokensOf(this.#diffCharacters + threadCharacters(this.threads.all)));
		this.#hello = $derived({
			round: this.rounds.current,
			threads: this.threads.onTheWire
		});
		this.#draft = $derived(this.submission.finished ? null : this.#snapshot());
		if (this.answerer.attached) this.layout.agentPanel.offer();
	}

	/** The unsent review as a draft keeps it; none once the review is over. */
	get draft(): Draft | null {
		return this.#draft;
	}

	/**
	 * Take in where the review stands, as the server says now: after a gap in
	 * what it pushed, the facts the pushes kept up to date are read again.
	 */
	learn(facts: ReviewResponse): void {
		this.rounds.reach(facts.round);
		this.noteAnswerer(facts.answerer_attached);
		this.answerer.report(facts.agent);
		this.answerer.showWork(facts.work);
	}

	/** An agent turned up, or went quiet long enough to count as gone; one that turns up is offered the panel. */
	noteAnswerer(attached: boolean): void {
		this.answerer.setAttached(attached);
		if (attached) this.layout.agentPanel.offer();
	}

	get restoredCount(): number {
		return this.#restoredCount;
	}

	dismissRestored(): void {
		this.#restoredCount = 0;
	}

	/** What handing this review over costs, in tokens, as far as this side can tell. */
	get weight(): number {
		return this.#weight;
	}

	/** The most lines one comment may cover. */
	get longestQuotedRange(): number {
		return this.limits.max_quoted_lines;
	}

	/**
	 * Keep the server told what this page holds, for as long as it is open:
	 * an agent that attaches later has no other way to learn the threads
	 * exist, and a restarted server knows only round one. Returns how to stop.
	 */
	tellServerThrough(connection: Greeter): () => void {
		return $effect.root(() => {
			$effect(() => connection.greet(this.#hello));
		});
	}

	/**
	 * Retake the diff with whitespace counted or not.
	 *
	 * Only git can answer this: which hunks vanish once whitespace stops
	 * counting is not something the browser can work out from what it has.
	 */
	async setIgnoreWhitespace(next: boolean): Promise<void> {
		await this.settings.change({ ignore_whitespace: next });
		try {
			await this.diff.take();
		} catch (error) {
			// Nobody is waiting on this but the reader, so it is said where they will see it
			this.conversation.note(diffNotTakenNote(error));
		}
	}

	/**
	 * Move the threads onto the review's diff as it now stands, and take it.
	 *
	 * The threads go first: the server already holds the new diff, and a
	 * thread left on old numbers would be kept that way in the draft. One
	 * retake is taken in at a time, so threads never follow onto a diff older
	 * than the one on screen. Whatever had moved on disk is in the diff taken,
	 * so the tree has nothing more to say — unless it moves again meanwhile.
	 */
	takeRetakenDiff(): Promise<FollowOutcome> {
		return this.#oneRetakeAtATime(() => this.#followAndTake());
	}

	/**
	 * Move the threads onto the review's diff as it now stands, leaving the
	 * diff on screen as it is: it was taken after the retake already.
	 */
	followThreads(): Promise<FollowOutcome> {
		return this.#oneRetakeAtATime(() => this.threads.follow());
	}

	/** Note what a retake did, and take the tick off what it rewrote. */
	noteRetake(outcome: FollowOutcome, changes: ChangesSince | null): void {
		this.lastRetake.note(outcome, changes);
		this.reading.forgetRewritten(changes);
	}

	#snapshot(): Draft {
		return {
			version: DRAFT_SHAPE,
			title: this.title,
			threads: this.threads.all,
			read: this.threads.reading.kept,
			writing: this.threads.writing.kept,
			reviewBody: this.submission.body,
			sent: this.threads.sentRounds,
			panel: this.conversation.turns,
			composer: this.conversation.composer.kept,
			issued: this.threads.issued,
			told: this.telling.heard
		};
	}

	#oneRetakeAtATime(retake: () => Promise<FollowOutcome>): Promise<FollowOutcome> {
		const taken = this.#retaking.then(retake);
		this.#retaking = taken.catch(() => undefined);
		return taken;
	}

	async #followAndTake(): Promise<FollowOutcome> {
		const moved = await this.threads.follow();
		this.diff.treeMoved.settle();
		await this.diff.take();
		return moved;
	}

	/** Read only what changed since the round the last retake was counted from. */
	async showChangesSinceRetake(): Promise<void> {
		const since = this.lastRetake.changedSinceKey;
		if (since === null) return;
		await this.diff.setBase(since);
	}
}
