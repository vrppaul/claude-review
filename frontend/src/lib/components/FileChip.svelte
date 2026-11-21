<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Chip from '$lib/ui/Chip.svelte';
	import { fileName } from '$lib/utils/paths';

	interface Props {
		/** A file the agent named, in what it said or in what it is working on, or one a check's code changed in. */
		path: string;
		/** The file pressing it takes the reader to, as whoever draws it decides; null where it leads nowhere. */
		leadsTo: string | null;
		/** What a test finds the chip by. */
		testId: string;
	}

	let { path, leadsTo, testId }: Props = $props();
	const review = useReview();

	// What a file that leads nowhere is said to be: the agent names a file
	// it has made, as it works, before the diff is taken again
	const NOT_IN_THE_DIFF = 'not in the diff yet';
</script>

{#if leadsTo !== null}
	<!-- Where the view on screen draws the file, the reader is taken there; where it draws none of
		it — a story that does not tell it, a narrower base — the files come on screen for it, whole,
		or the file the change did not touch is read alone -->
	<Chip voice="agent" names="place" {testId} title={path} onclick={() => review.navigator.showFile(leadsTo)}>
		{fileName(path)}
	</Chip>
{:else}
	<!-- Named, and nothing to take the reader to: said, not a way there -->
	<Chip voice="agent" names="place" outOfReach {testId} title="{path} — {NOT_IN_THE_DIFF}">
		{fileName(path)}<span class="sr-only"> — {NOT_IN_THE_DIFF}</span>
	</Chip>
{/if}
