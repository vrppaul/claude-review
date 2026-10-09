<script lang="ts">
	import type { Thread, DiffFile } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { isDrawn } from '$lib/anchors/placement';
	import { useReview } from '$lib/review/context';
	import { followWords, PHRASE_BREAK } from '$lib/review/follow-words';

	const review = useReview();

	let failed = $state<string | null>(null);

	// How long the retaken bar stands. Long enough to read twice, short
	// enough that it is not still there when the reader looks up again — it
	// reports something that already happened and needs no answer.
	const SHOWN_FOR = 12_000;

	const moved = $derived(review.diff.treeMoved.count);
	const retaken = $derived(review.lastRetake.outcome);
	// Threads the base on screen cannot draw. They are not lost — they are
	// anchored to the review's own diff — but saying nothing would leave the
	// reader counting a review they can only see part of.
	const offScreen = $derived(review.threads.all.filter((c) => !isDrawn(c, review.diff.files, { removedLines: false })));
	// The diff the list of them was opened over. Every diff taken after it —
	// another base, a retake — starts folded, so the list is never left open
	// from a screen the reader has left.
	let listedOver = $state.raw<DiffFile[] | null>(null);
	const listing = $derived(listedOver === review.diff.files);

	/** Take the reader back to the whole diff, and to the thread they picked. */
	async function goTo(comment: Thread) {
		failed = null;
		try {
			await review.diff.showWholeReview();
			review.navigator.reveal(comment);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the whole diff again';
		}
	}
	// The one thing a retake can lose: a thread whose lines are gone. It keeps
	// what it was written against, and that is what "show it" goes to.
	const stranded = $derived(review.threads.all.find((comment) => comment.anchor.outdated));

	// Each retake starts the clock afresh: what it says is about that one
	$effect(() => {
		if (!review.lastRetake.outcome) return;
		const timer = setTimeout(() => review.lastRetake.dismiss(), SHOWN_FOR);
		return () => clearTimeout(timer);
	});

	/** What the retaken bar says happened, in the order it matters. */
	function whatChanged(): string {
		const count = review.lastRetake.changedCount;
		const since = review.lastRetake.changedSince;
		if (!review.lastRetake.changedKnown) {
			// Every tick has just been dropped, and saying "nothing changed"
			// here would be the opposite of what the reader must do next
			return 'Diff retaken — what changed could not be worked out, so nothing is marked read';
		}
		if (since === null) return 'Diff retaken';
		if (count === 0) return `Diff retaken — nothing has changed since round ${since}`;
		return `Diff retaken — ${count} ${count === 1 ? 'file has' : 'files have'} changed since round ${since}`;
	}

	async function showWhatChanged() {
		failed = null;
		try {
			await review.showChangesSinceRetake();
			review.lastRetake.dismiss();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the diff against that round';
		}
	}

	async function showEverything() {
		failed = null;
		try {
			await review.diff.showWholeReview();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the whole diff again';
		}
	}

	async function retake() {
		failed = null;
		try {
			await review.diff.retake();
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Could not take the diff again';
		}
	}
</script>

{#if moved > 0}
	<!-- Amber, not the mark colour: this is the code moving, not the reader's
		own mark. Never a swap: whoever is mid-sentence decides when. -->
	<div
		data-testid="tree-moved"
		class="cr-notice cr-notice-moved flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<svg
			class="h-3 w-3 shrink-0"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			aria-hidden="true"
		>
			<path d="M8 4.5v4"></path>
			<path d="M8 11.2v.3"></path>
			<circle cx="8" cy="8" r="6"></circle>
		</svg>
		<span>
			The working tree has moved on — {moved}
			{moved === 1 ? 'file has' : 'files have'} changed since this diff was taken.
		</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="retake-error" class="text-error">{failed}</span>
		{/if}
		<button data-testid="retake-diff" class="btn btn-ghost btn-xs" onclick={retake}>Retake</button>
		<button data-testid="dismiss-moved" class="btn btn-ghost btn-xs" onclick={() => review.diff.treeMoved.dismiss()}>
			Dismiss
		</button>
	</div>
{:else if retaken}
	<!-- Says what happened to the threads, because that is what the reader
		stands to lose in a retake -->
	<div
		data-testid="diff-retaken"
		class="cr-notice cr-notice-taken flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<svg
			class="h-3 w-3 shrink-0"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.6"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M3 8.5l3.2 3.2L13 5"></path>
		</svg>
		<span>
			{[whatChanged(), ...followWords(retaken)].join(PHRASE_BREAK)}
		</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="retaken-error" class="text-error">{failed}</span>
		{/if}
		{#if review.lastRetake.changedSince !== null && review.lastRetake.changedCount > 0}
			<button data-testid="show-what-changed" class="btn btn-ghost btn-xs" onclick={showWhatChanged}>
				Show what changed
			</button>
		{/if}
		{#if stranded}
			<button
				data-testid="show-outdated"
				class="btn btn-ghost btn-xs"
				onclick={() => review.navigator.reveal(stranded)}
			>
				Show it
			</button>
		{/if}
		<button data-testid="dismiss-retaken" class="btn btn-ghost btn-xs" onclick={() => review.lastRetake.dismiss()}>
			Dismiss
		</button>
	</div>
{/if}

{#if review.diff.narrowed}
	<!-- A state, not news: no Dismiss, because dismissing it would leave the
		reader looking at part of the review with nothing saying so. The way
		out is the only other thing here. -->
	<div
		data-testid="narrowed-to"
		class="cr-notice cr-notice-taken flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<svg
			class="h-3 w-3 shrink-0"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M2.5 5h9"></path>
			<path d="M9 2.5L11.5 5 9 7.5"></path>
			<path d="M13.5 11h-9"></path>
			<path d="M7 8.5L4.5 11 7 13.5"></path>
		</svg>
		<span>
			{#if review.diff.files.length === 0}
				Nothing has changed — {review.diff.phrase}.
			{:else}
				Showing {review.diff.phrase} — {review.diff.files.length}
				{review.diff.files.length === 1 ? 'file' : 'files'}.
			{/if}
			{#if offScreen.length > 0}
				{offScreen.length}
				{offScreen.length === 1 ? 'thread is' : 'threads are'} not on this screen.
			{/if}
		</span>
		<div class="flex-1"></div>
		{#if failed}
			<span data-testid="narrow-error" class="text-error">{failed}</span>
		{/if}
		{#if offScreen.length > 0}
			<button
				data-testid="list-off-screen"
				class="btn btn-ghost btn-xs"
				aria-expanded={listing}
				onclick={() => (listedOver = listing ? null : review.diff.files)}
			>
				{listing ? 'Hide them' : 'List them'}
			</button>
		{/if}
		<button data-testid="show-everything" class="btn btn-ghost btn-xs" onclick={showEverything}>
			Show the whole diff
		</button>
	</div>

	{#if listing}
		<!-- Where they are, so a count is not the end of the road. Picking one
			puts the whole diff back and goes to it: it is anchored there, and
			that is the only screen that can draw it. -->
		<div data-testid="off-screen-list" class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-1.5">
			{#each offScreen as comment (comment.id)}
				<button
					data-testid="off-screen-thread"
					class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-base-200"
					onclick={() => goTo(comment)}
				>
					<span class="cr-comment-ref shrink-0 font-mono text-xs">
						{anchorShortPlace(comment.anchor)}
					</span>
					<span class="cr-faint min-w-0 flex-1 truncate text-xs">{comment.body}</span>
				</button>
			{/each}
			<p class="cr-faint px-2 pt-1 text-xs">They are still in the review, and still go out with the round.</p>
		</div>
	{/if}
{/if}
