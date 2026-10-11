<script lang="ts">
	import type { Thread, DiffFile } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { isDrawn } from '$lib/anchors/placement';
	import { useReview } from '$lib/review/context';
	import { counted } from '$lib/utils/words';
	import { Attempt } from './attempt.svelte';
	import Icon from './Icon.svelte';

	const review = useReview();
	const widening = new Attempt();

	// Threads the base on screen cannot draw. They are not lost — they are
	// anchored to the review's own diff — but saying nothing would leave the
	// reader counting a review they can only see part of.
	const offScreen = $derived(
		review.threads.onLines
			.filter(({ lines }) => !isDrawn(lines, review.diff.files, { removedLines: false }))
			.map(({ thread }) => thread)
	);
	// The diff the list of them was opened over. Every diff taken after it —
	// another base, a retake — starts folded, so the list is never left open
	// from a screen the reader has left.
	let listedOver = $state.raw<DiffFile[] | null>(null);
	const listing = $derived(listedOver === review.diff.files);

	/** Take the reader back to the whole diff, and to the thread they picked. */
	async function goTo(thread: Thread) {
		if (await widening.run(() => review.diff.showWholeReview())) review.navigator.reveal(thread);
	}
</script>

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
	{#if widening.failed}
		<span data-testid="narrow-error" class="text-error">{widening.failed}</span>
	{/if}
	{#if offScreen.length > 0}
		<button
			type="button"
			data-testid="list-off-screen"
			class="btn btn-ghost btn-xs"
			aria-expanded={listing}
			onclick={() => (listedOver = listing ? null : review.diff.files)}
		>
			{listing ? 'Hide them' : 'List them'}
		</button>
	{/if}
	<button
		type="button"
		data-testid="show-everything"
		class="btn btn-ghost btn-xs"
		onclick={() => widening.run(() => review.diff.showWholeReview())}
	>
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
				type="button"
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
