<script lang="ts">
	import type { Thread, DiffFile } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { isDrawn } from '$lib/anchors/placement';
	import { useReview } from '$lib/review/context';
	import { followWords, PHRASE_BREAK } from '$lib/review/follow-words';
	import { messageOf } from '$lib/utils/errors';
	import { counted } from '$lib/utils/words';
	import Icon from './Icon.svelte';

	// What a bar says when the diff it asked for could not be taken, and nothing said why
	const WHOLE_DIFF_NOT_TAKEN = 'Could not take the whole diff again';
	const ROUND_DIFF_NOT_TAKEN = 'Could not take the diff against that round';
	const RETAKE_FAILED = 'Could not take the diff again';

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
	const offScreen = $derived(
		review.threads.all.filter((thread) => !isDrawn(thread, review.diff.files, { removedLines: false }))
	);
	// The diff the list of them was opened over. Every diff taken after it —
	// another base, a retake — starts folded, so the list is never left open
	// from a screen the reader has left.
	let listedOver = $state.raw<DiffFile[] | null>(null);
	const listing = $derived(listedOver === review.diff.files);

	/** Do what a button asks, saying why if it could not be done; whether it was. */
	async function attempt(act: () => Promise<unknown>, fallback: string): Promise<boolean> {
		failed = null;
		try {
			await act();
			return true;
		} catch (error) {
			failed = messageOf(error, fallback);
			return false;
		}
	}

	/** Take the reader back to the whole diff, and to the thread they picked. */
	async function goTo(thread: Thread) {
		if (await attempt(() => review.diff.showWholeReview(), WHOLE_DIFF_NOT_TAKEN)) review.navigator.reveal(thread);
	}
	// The one thing a retake can lose: a thread whose lines are gone. It keeps
	// what it was written against, and that is what "show it" goes to.
	const stranded = $derived(review.threads.all.find((thread) => thread.anchor.outdated));

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
		return `Diff retaken — ${counted(count, 'file has', 'files have')} changed since round ${since}`;
	}

	async function showWhatChanged() {
		if (await attempt(() => review.showChangesSinceRetake(), ROUND_DIFF_NOT_TAKEN)) review.lastRetake.dismiss();
	}

	function showEverything() {
		void attempt(() => review.diff.showWholeReview(), WHOLE_DIFF_NOT_TAKEN);
	}

	function retake() {
		void attempt(() => review.diff.retake(), RETAKE_FAILED);
	}
</script>

{#if moved > 0}
	<!-- Amber, not the mark colour: this is the code moving, not the reader's
		own mark. Never a swap: whoever is mid-sentence decides when. -->
	<div
		data-testid="tree-moved"
		class="cr-notice cr-notice-moved flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
	>
		<Icon name="notice" class="h-3 w-3 shrink-0" />
		<span>
			The working tree has moved on — {counted(moved, 'file has', 'files have')} changed since this diff was taken.
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
		<Icon name="check" class="h-3 w-3 shrink-0" />
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
		<Icon name="compare" class="h-3 w-3 shrink-0" />
		<span>
			{#if review.diff.files.length === 0}
				Nothing has changed — {review.diff.phrase}.
			{:else}
				Showing {review.diff.phrase} — {counted(review.diff.files.length, 'file', 'files')}.
			{/if}
			{#if offScreen.length > 0}
				{counted(offScreen.length, 'thread is', 'threads are')} not on this screen.
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
			{#each offScreen as thread (thread.id)}
				<button
					data-testid="off-screen-thread"
					class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-base-200"
					onclick={() => goTo(thread)}
				>
					<span class="cr-comment-ref shrink-0 font-mono text-xs">
						{anchorShortPlace(thread.anchor)}
					</span>
					<span class="cr-faint min-w-0 flex-1 truncate text-xs">{thread.body}</span>
				</button>
			{/each}
			<p class="cr-faint px-2 pt-1 text-xs">They are still in the review, and still go out with the round.</p>
		</div>
	{/if}
{/if}
