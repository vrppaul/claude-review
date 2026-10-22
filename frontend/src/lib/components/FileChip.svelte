<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Chip from '$lib/ui/Chip.svelte';
	import { fileName } from '$lib/utils/paths';

	interface Props {
		/** A file the agent named, in what it said or in what it is working on. */
		path: string;
		/** What a test finds the chip by. */
		testId: string;
	}

	let { path, testId }: Props = $props();
	const review = useReview();

	// What a file the diff does not hold is said to be: the agent names a file
	// it has made, as it works, before the diff is taken again
	const NOT_IN_THE_DIFF = 'not in the diff yet';

	// Asked of the review's own diff: a narrower base on screen leaves out files the review holds
	const held = $derived(review.diff.holds(path));
</script>

{#if held}
	<!-- Where the view on screen draws the file, the reader is taken there; where it draws none of
		it — a story that does not tell it, a narrower base — the files come on screen for it, whole -->
	<Chip voice="agent" names="place" {testId} title={path} onclick={() => review.navigator.showFile(path)}>
		{fileName(path)}
	</Chip>
{:else}
	<!-- Named, and nothing to take the reader to: said, not a way there -->
	<Chip voice="agent" names="place" outOfReach {testId} title="{path} — {NOT_IN_THE_DIFF}">
		{fileName(path)}<span class="sr-only"> — {NOT_IN_THE_DIFF}</span>
	</Chip>
{/if}
