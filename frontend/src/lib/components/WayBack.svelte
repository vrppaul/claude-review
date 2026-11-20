<script lang="ts">
	import { useReview } from '$lib/review/context';
	import type { LinePlace } from '$lib/types';
	import BackTo from '$lib/ui/BackTo.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import { fileName } from '$lib/utils/paths';

	interface Props {
		/** Where it stands: across the foot of the column beside what is read, or at the foot of its rail. */
		stands: 'foot' | 'rail';
	}

	let { stands }: Props = $props();
	const review = useReview();

	const place = $derived(review.wayBack.top);

	/** A place as the reader knows it: a file, by its name or its whole path, and the line read from, if any. */
	function placeSaid(file: string, line: LinePlace | null): string {
		return line === null ? file : `${file}:${line.number}`;
	}
</script>

<!-- The way back to where the reader was before the page took them to a line: across the column's foot, or as its
	icon on the rail of the column put away, its words on the pointer -->
{#if place}
	{@const named = placeSaid(fileName(place.path), place.line)}
	{#if stands === 'foot'}
		<BackTo
			place={named}
			whole={placeSaid(place.path, place.line)}
			testId="go-back"
			onclick={() => review.navigator.goBack()}
		/>
	{:else}
		<IconButton
			tone="quiet"
			size="xs"
			shape="square"
			label="Back to {named}"
			testId="go-back-on-rail"
			onclick={() => review.navigator.goBack()}
		>
			<Icon name="chevron" size="sm" pointing="left" />
		</IconButton>
	{/if}
{/if}
