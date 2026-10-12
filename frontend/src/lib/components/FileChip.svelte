<script lang="ts">
	import { useReview } from '$lib/review/context';
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

	const inTheDiff = $derived(review.diff.files.some((file) => file.path === path));
</script>

{#if inTheDiff}
	<button
		type="button"
		data-testid={testId}
		class="cr-thread-chip cr-thread-chip-agent"
		title={path}
		onclick={() => review.sections.showFile(path)}
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
