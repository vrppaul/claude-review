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
import type { PageTheme } from '$lib/reader/page-theme.svelte';
import type { ReplySound } from '$lib/reader/reply-sound';
import type { Settings } from '$lib/reader/settings.svelte';
import { Answerer } from '$lib/review/answerer.svelte';
import { Clock } from '$lib/review/clock.svelte';
import { CommentFields } from '$lib/review/comment-fields';
import { Conversation } from '$lib/review/conversation.svelte';
import { FileSections } from '$lib/dom/file-sections';
import { Jumps } from '$lib/dom/jump';
import { ReadingParts } from '$lib/dom/reading-parts';
import { LastRetake } from '$lib/review/last-retake.svelte';
import { diffNotTakenNote } from '$lib/review/panel-notes';
import { ReadingProgress } from '$lib/review/reading-progress.svelte';
import { FilesReading } from '$lib/review/reading-view';
import { ReadingViews } from '$lib/review/reading-views.svelte';
import { ReviewDiff } from '$lib/review/review-diff.svelte';
import { ReviewStory } from '$lib/review/review-story.svelte';
import type { StepListed } from '$lib/review/story-contents';
import { StoryReading } from '$lib/review/story-reading';
import { isAwaited } from '$lib/review/story-wait';
import { Rounds } from '$lib/review/rounds.svelte';
import { ServerLink } from '$lib/review/server-link.svelte';
import { Submission } from '$lib/review/submission.svelte';
import { Telling } from '$lib/review/telling.svelte';
import { Navigator } from '$lib/review/navigator';
import { Threads } from '$lib/review/threads.svelte';
import type {
	ChangesSince,
	DiffResponse,
	FollowOutcome,
	HeldThread,
	ReviewMode,
	ReviewResponse,
	SaidInPanel,
	SendLimits,
	SessionHello,
	StoryHeld
} from '$lib/types';
import { DRAFT_SHAPE, type Draft, emptyDraft } from '$lib/drafts/draft-shapes';
import { diffCharacters, threadCharacters, tokensOf } from '$lib/review/weight';

/**
 * What a review opens on: what the server says it is, its first diff, any
 * unsent draft, and the threads and the panel's conversation it holds.
 */
export interface Opening {
	facts: ReviewResponse;
	firstDiff: DiffResponse;
	draft: Draft | null;
	/** Whether a draft this browser kept could not be read, and was set aside rather than opened from. */
	draftSetAside: boolean;
	/** What the review holds of its threads: taken in only with no draft to open from. */
	held: HeldThread[];
	/** What the review holds as said in the panel: drawn whatever the draft holds, which adds what it does not. */
	said: SaidInPanel[];
	/** The story the review holds, if the agent told one. */
	story: StoryHeld | null;
}

/** Whoever carries what the page holds to the server. */
export interface Greeter {
	greet: (hello: SessionHello) => void;
}

/** What belongs to the reader rather than to the review, and outlives it. */
export interface ReaderParts {
	settings: Settings;
	layout: PageLayout;
	sound: ReplySound;
	theme: PageTheme;
}

/**
 * The parts of the story a draft says the reader had read through, where it
 * was kept in this run of the review. Each run is told its story anew: of
 * that one, a draft kept in another run says nothing.
 */
function partsReadInRun(kept: Draft, run: string): readonly string[] {
	return kept.told?.instance === run ? kept.storyRead : [];
}

export class Review {
	/** What is under review — which repository, and against what. */
	readonly title: string;
	/** What makes it the same review whenever it is opened: its draft is kept under it. */
	readonly identity: string;
	readonly mode: ReviewMode;
	/** What the server takes: pasted images, and the lines one comment covers. */
	readonly limits: SendLimits;

	readonly settings: Settings;
	readonly layout: PageLayout;
	readonly sound: ReplySound;
	/** The theme the page carries, which the tab's icon is painted in. */
	readonly theme: PageTheme;

	readonly rounds: Rounds;
	/** Whether the review still runs for this page, and how it ended once it has. */
	readonly link = new ServerLink();
	/** How far the server's telling has got for this page. */
	readonly telling: Telling;
	readonly answerer: Answerer;
	readonly diff: ReviewDiff;
	/** How far the reader has got through the files. */
	readonly reading: ReadingProgress;
	readonly lastRetake = new LastRetake();
	readonly threads: Threads;
	readonly submission: Submission;
	readonly conversation: Conversation;
	/** The story the agent told of the change, if it told one. */
	readonly story: ReviewStory;
	readonly guide: Guide;
	// Where the page is taking the reader: one jump at a time, whether to a section or to a part of the story
	readonly #jumps = new Jumps();
	readonly sections = new FileSections(this.#jumps);
	/** The parts of the story on the page — its overview, each chapter, what it leaves out — and which is being read. */
	readonly parts = new ReadingParts(this.#jumps);
	/** The ways the review is read — file by file, or as the story told of it — and which is on screen. */
	readonly views: ReadingViews;
	readonly navigator: Navigator;
	readonly commentFields = new CommentFields();
	/** The time now, for whatever says how long ago something was. */
	readonly clock = new Clock();

	// How many threads came back from the draft, so the reader is told rather
	// than left to wonder where they came from; zero once they have seen it
	#restoredCount: number;
	// Whether a kept draft could not be read and was set aside, so the reader
	// is told why their unsent work is not here; false once they have seen it
	#draftSetAside: boolean;
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

	constructor({ facts, firstDiff, draft, draftSetAside, held, said, story }: Opening, reader: ReaderParts) {
		this.title = facts.title;
		this.identity = facts.identity;
		this.mode = facts.mode;
		this.limits = facts.limits;
		this.settings = reader.settings;
		this.layout = reader.layout;
		this.sound = reader.sound;
		this.theme = reader.theme;

		// What the review picks up: the draft it opened from, or nothing yet
		const kept = draft ?? emptyDraft(facts.round);
		// A server restarted mid-review comes back at round one: the draft knows better
		this.rounds = new Rounds(facts.round);
		this.rounds.reach(kept.round);
		this.telling = new Telling({ instance: facts.instance, sequence: facts.sequence }, kept.told);
		this.answerer = new Answerer(facts.answerer_attached, facts.agent, facts.work);
		this.diff = new ReviewDiff(firstDiff, () => this.settings.current.ignore_whitespace);
		this.reading = new ReadingProgress(kept.files);
		this.threads = new Threads(this.rounds, kept, this.commentFields);
		// A page with no draft — another browser, a private window — would
		// otherwise say it holds no threads, and the review would forget them
		if (draft === null) this.threads.adopt(held);
		this.submission = new Submission(this.threads, this.rounds, this.answerer, this.link, kept.reviewBody);
		this.conversation = new Conversation(kept.panel, said, kept.composer, () => this.threads.all);
		this.story = new ReviewStory({
			canBeTold: facts.takes_a_story,
			held: story,
			asking: facts.story_asking,
			partsRead: partsReadInRun(kept, facts.instance),
			takeOnScreen: () => this.diff.takeOnScreen,
			agentAttached: () => this.answerer.attached,
			sayInPanel: (words) => this.conversation.note(words)
		});
		this.guide = new Guide(this.answerer, this.threads.writing, facts.release);
		this.views = new ReadingViews(
			{
				files: new FilesReading(this.diff, this.threads, this.reading),
				story: new StoryReading(this.story, this.threads)
			},
			this.layout.readingView,
			this.story.canBeTold && this.storyViewOpens,
			this.diff
		);
		this.navigator = new Navigator(this.threads, this.sections, this.views);
		// What the draft kept that had not gone out: the header's "unsent" counts the same
		this.#restoredCount = $state(draft === null ? 0 : this.threads.unsent.length);
		this.#draftSetAside = $state(draftSetAside);
		this.#diffCharacters = $derived(diffCharacters(this.diff.files));
		this.#weight = $derived(tokensOf(this.#diffCharacters + threadCharacters(this.threads.all)));
		this.#hello = $derived({
			round: this.rounds.current,
			threads: this.threads.onTheWire
		});
		// A review stopped under the reader keeps its draft for when it is opened again
		this.#draft = $derived(this.link.ending === 'finished' ? null : this.#snapshot());
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
		this.story.learnAsking(facts.story_asking);
	}

	/** An agent turned up, or went quiet long enough to count as gone; one that turns up is offered the panel. */
	noteAnswerer(attached: boolean): void {
		this.answerer.setAttached(attached);
		if (attached) this.layout.agentPanel.offer();
	}

	/** Whether a question asked in a thread reaches anybody now: an agent is there, and the review is reached. */
	get canAsk(): boolean {
		return this.answerer.attached && this.link.connected;
	}

	/**
	 * The step of the story being read, as its chapter lists it: the one
	 * whose section is at the top of the reading area. None while that
	 * section is no step's, or no section is there at all.
	 */
	get stepBeingRead(): StepListed | null {
		return this.story.contents.stepAt(this.sections.sectionInView);
	}

	get restoredCount(): number {
		return this.#restoredCount;
	}

	dismissRestored(): void {
		this.#restoredCount = 0;
	}

	get draftSetAside(): boolean {
		return this.#draftSetAside;
	}

	dismissSetAside(): void {
		this.#draftSetAside = false;
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
		await this.#takeDiffAgain();
	}

	/**
	 * Take in the reader's settings again, as another tab may have changed
	 * them: the diff is taken again where whether whitespace counts changed,
	 * and a story is asked for where stories were turned on, as after a gap
	 * in what the server told. Turned off, they stop nothing here: the way
	 * to stop a story is in reach wherever one is being written. Settings
	 * that cannot be read leave the review as it was.
	 */
	async readSettingsAgain(): Promise<void> {
		const whitespaceIgnored = this.settings.current.ignore_whitespace;
		try {
			await this.settings.readAgain();
		} catch {
			// A server that cannot say leaves this tab reading as it was
			return;
		}
		if (this.settings.current.ignore_whitespace !== whitespaceIgnored) await this.#takeDiffAgain();
		await this.wantStory();
	}

	/**
	 * Whether the story view opens without the reader being asked first:
	 * they turned stories on; or a story is held already, told by an agent of
	 * its own accord and so paid for; or one is on its way, asked for from
	 * another page of this review, whose choice this page was never told.
	 * Wherever the header says a story is being written, the way to stop it
	 * must be in reach: the wait screen's Stop while no story is held; over
	 * a story a round moved the code on under, drawn while it is told again,
	 * the gear, turning stories off. Where none of these holds, reading the
	 * review as its story means having one written, which spends the
	 * agent's tokens: the reader is asked before that, and a review they
	 * open is read by its files though they chose the story last.
	 */
	get storyViewOpens(): boolean {
		return this.settings.current.stories || this.story.held !== null || isAwaited(this.story.wait);
	}

	/**
	 * Ask the agent for a story where the reader wants one and has none
	 * coming: they turned stories on, one can be told of this review, no
	 * story held is current and none was asked for. Called as the page
	 * opens, after a gap in what the server told, and once the diff is taken
	 * again. Never where the reader stopped the one asked for: a reload does
	 * not start it again.
	 */
	async wantStory(): Promise<void> {
		if (this.settings.current.stories && this.story.canBeTold && this.story.wait?.kind === 'unasked') {
			await this.story.askFor();
		}
	}

	/**
	 * Turn stories on, for this review and every later one, and ask for this
	 * review's wherever none is on its way. One the reader stopped is asked
	 * for again, whether they stopped it by hand or by turning stories off:
	 * turning them on says a story is wanted.
	 */
	async turnStoriesOn(): Promise<void> {
		await this.settings.change({ stories: true });
		if (this.story.canBeAskedFor) await this.story.askFor();
	}

	/**
	 * Turn stories off, for this review and every later one. A story still
	 * awaited is stopped: it would spend the tokens the reader turned
	 * stories off to keep. With none held the files come on screen: the
	 * story view has no story to draw, and the reader has said they want
	 * none. A story held is paid for, and stays to be read; one a round
	 * moved the code on under is told again no more.
	 */
	async turnStoriesOff(): Promise<void> {
		if (this.story.held === null) this.views.showFiles();
		await this.settings.change({ stories: false });
		if (isAwaited(this.story.wait)) await this.story.stop();
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
			threads: this.threads.all,
			read: this.threads.reading.kept,
			writing: this.threads.writing.kept,
			reviewBody: this.submission.body,
			sent: this.threads.sentRounds,
			panel: this.conversation.turns,
			composer: this.conversation.composer.kept,
			issued: this.threads.issued,
			told: this.telling.heard,
			files: this.reading.kept,
			storyRead: this.story.progress.kept,
			round: this.rounds.current
		};
	}

	/** Take the diff again with whitespace counted as the settings now say. */
	async #takeDiffAgain(): Promise<void> {
		try {
			await this.diff.take();
		} catch (error) {
			// Nobody is waiting on this but the reader, so it is said where they will see it
			this.conversation.note(diffNotTakenNote(error));
		}
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

	/**
	 * Read only what changed since the round the last retake was counted
	 * from: the files against that base, which come on screen for it.
	 */
	async showChangesSinceRetake(): Promise<void> {
		const since = this.lastRetake.changedSinceKey;
		if (since === null) return;
		await this.diff.setBase(since);
		this.views.showFiles();
	}
}
