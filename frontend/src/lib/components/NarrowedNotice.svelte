<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { threadsNotDrawnIn } from '$lib/review/reading-view';
	import { plainWords } from '$lib/utils/plain-words';
	import { counted } from '$lib/utils/words';
	import Icon from './Icon.svelte';

	const review = useReview();

	// Threads the base on screen cannot draw. They are not lost — they are
	// anchored to the review's own diff — but saying nothing would leave the
	// reader counting a review they can only see part of.
	const offScreen = $derived(threadsNotDrawnIn(review.views.onScreen, review.threads));
	// The diff the list of them was opened over. Every diff taken after it —
	// another base, a retake — starts folded, so the list is never left open
	// from a screen the reader has left.
	let listedOver = $state.raw<DiffFile[] | null>(null);
	const listing = $derived(listedOver === review.diff.files);
	// What the list's button says, while the list is shown and while it is not, of one thread or of several
	const LIST_WORDS = { shown: { one: 'Hide it', many: 'Hide them' }, folded: { one: 'List it', many: 'List them' } };
	const listWords = $derived(LIST_WORDS[listing ? 'shown' : 'folded']);
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
	{#if review.diff.wholeReviewFailed}
		<span data-testid="narrow-error" class="text-error">{review.diff.wholeReviewFailed}</span>
	{/if}
	{#if offScreen.length > 0}
		<button
			type="button"
			data-testid="list-off-screen"
			class="btn btn-ghost btn-xs"
			aria-expanded={listing}
			onclick={() => (listedOver = listing ? null : review.diff.files)}
		>
			{offScreen.length === 1 ? listWords.one : listWords.many}
		</button>
	{/if}
	<button
		type="button"
		data-testid="show-everything"
		class="btn btn-ghost btn-xs"
		onclick={() => review.diff.showWholeReview()}
	>
		Show the whole diff
	</button>
</div>

{#if listing}
	<!-- Where they are, so a count is not the end of the road. Picking one
		goes to it, which puts the whole diff back first: it is anchored
		there, and that is the only screen that can draw it. -->
	<div data-testid="off-screen-list" class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-1.5">
		{#each offScreen as thread (thread.id)}
			<button
				type="button"
				data-testid="off-screen-thread"
				class="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-base-200"
				onclick={() => review.navigator.reveal(thread)}
			>
				<span class="cr-comment-ref shrink-0 font-mono text-xs">
					{anchorShortPlace(thread.anchor)}
				</span>
				<span class="cr-faint min-w-0 flex-1 truncate text-xs">{plainWords(thread.body)}</span>
			</button>
		{/each}
		<p class="cr-faint px-2 pt-1 text-xs">They are still in the review, and still go out with the round.</p>
	</div>
{/if}
