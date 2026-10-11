<script lang="ts">
	import { useReview } from '$lib/review/context';
	import NarrowedNotice from './NarrowedNotice.svelte';
	import RetakenNotice from './RetakenNotice.svelte';
	import TreeMovedNotice from './TreeMovedNotice.svelte';

	const review = useReview();

	// How long the retaken bar stands. Long enough to read twice, short
	// enough that it is not still there when the reader looks up again — it
	// reports something that already happened and needs no answer.
	const SHOWN_FOR = 12_000;

	// Each retake starts the clock afresh: what it says is about that one
	$effect(() => {
		if (!review.lastRetake.outcome) return;
		const timer = setTimeout(() => review.lastRetake.dismiss(), SHOWN_FOR);
		return () => clearTimeout(timer);
	});
</script>

<!-- What the review has to say about the diff on screen, a bar each, each
	saying its own failures: the tree moving on outranks the news of the last
	retake, and a narrower base is said beside either -->
{#if review.diff.treeMoved.count > 0}
	<TreeMovedNotice />
{:else if review.lastRetake.outcome}
	<RetakenNotice retaken={review.lastRetake.outcome} />
{/if}

{#if review.diff.narrowed}
	<NarrowedNotice />
{/if}
