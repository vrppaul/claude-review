<script lang="ts">
	import { tick } from 'svelte';
	import { useReview } from '$lib/review/context';
	import { fileName } from '$lib/utils/paths';
	import { Attempt } from './attempt.svelte';

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
	const going = new Attempt();

	/** Take the reader to the file: under a narrower base, the whole review comes back first, and the file once it is drawn. */
	async function goToFile() {
		if (review.diff.narrowed && !(await going.run(() => review.diff.showWholeReview()))) return;
		await tick();
		review.navigator.showFile(path);
	}
</script>

{#if held}
	<button
		type="button"
		data-testid={testId}
		class="cr-thread-chip cr-thread-chip-agent"
		title={going.failed ?? path}
		onclick={goToFile}
	>
		{fileName(path)}
	</button>
{:else}
	<!-- Named, and nothing to take the reader to: said, not a way there -->
	<span
		data-testid={testId}
		class="cr-thread-chip cr-thread-chip-agent cr-thread-chip-elsewhere"
		title="{path} — {NOT_IN_THE_DIFF}"
	>
		{fileName(path)}<span class="sr-only"> — {NOT_IN_THE_DIFF}</span>
	</span>
{/if}
