<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { threadsNotDrawnIn } from '$lib/review/reading-view';
	import Button from '$lib/ui/Button.svelte';
	import NoticeBar from '$lib/ui/NoticeBar.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { plainWords } from '$lib/utils/plain-words';
	import { counted, type CountedWords, FILES, wordsFor } from '$lib/utils/words';

	// What the list's button says, while the list is shown and while it is not, of one thread or of several
	const LIST_WORDS = { shown: { one: 'Hide it', many: 'Hide them' }, folded: { one: 'List it', many: 'List them' } };
	// What the threads this screen does not draw are said to be, counted
	const THREADS_BEING: CountedWords = { one: 'thread is', many: 'threads are' };

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
	const listWords = $derived(LIST_WORDS[listing ? 'shown' : 'folded']);
</script>

<!-- A state, not news: no Dismiss, because dismissing it would leave the
	reader looking at part of the review with nothing saying so. The way
	out is the only other thing here. -->
<NoticeBar tone="reader" icon="compare" testId="narrowed-to">
	{#if review.diff.files.length === 0}
		Nothing has changed — {review.diff.phrase}.
	{:else}
		Showing {review.diff.phrase} — {counted(review.diff.files.length, FILES)}.
	{/if}
	{#if offScreen.length > 0}
		{counted(offScreen.length, THREADS_BEING)} not on this screen.
	{/if}
	{#snippet actions()}
		{#if review.diff.wholeReviewFailed}
			<span data-testid="narrow-error" class="text-error">{review.diff.wholeReviewFailed}</span>
		{/if}
		{#if offScreen.length > 0}
			<Button
				tone="quiet"
				size="xs"
				testId="list-off-screen"
				aria-expanded={listing}
				onclick={() => (listedOver = listing ? null : review.diff.files)}
			>
				{wordsFor(offScreen.length, listWords)}
			</Button>
		{/if}
		<Button tone="quiet" size="xs" testId="show-everything" onclick={() => review.diff.showWholeReview()}>
			Show the whole diff
		</Button>
	{/snippet}
</NoticeBar>

{#if listing}
	<!-- Where they are, so a count is not the end of the road. Picking one
		goes to it, which puts the whole diff back first: it is anchored
		there, and that is the only screen that can draw it. -->
	<div data-testid="off-screen-list" class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-1.5">
		{#each offScreen as thread (thread.id)}
			<!-- A row a thread: where it hangs, and what it says -->
			<Row names="path" testId="off-screen-thread" onclick={() => review.navigator.reveal(thread)}>
				{#snippet label()}
					<span class="cr-comment-ref">{anchorShortPlace(thread.anchor)}</span>
				{/snippet}
				{#snippet said()}
					{plainWords(thread.body)}
				{/snippet}
			</Row>
		{/each}
		<p class="cr-faint px-2 pt-1 text-xs">They are still in the review, and still go out with the round.</p>
	</div>
{/if}
