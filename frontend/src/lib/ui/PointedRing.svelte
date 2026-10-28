<script lang="ts">
	import type { PointedPart } from '$lib/dom/part-picking';
	import Chip from './Chip.svelte';
	import { namePlace } from './pointed';

	interface Props {
		/** The part pointed at: its name, and where it stands in the window. */
		part: PointedPart;
		testId: string;
	}

	let { part, testId }: Props = $props();

	let windowWidth = $state(0);
	let windowHeight = $state(0);
	let nameWidth = $state(0);
	let nameHeight = $state(0);

	// Under the part, over it, or in its foot: wherever the window shows it
	const placed = $derived(
		namePlace(part, { width: nameWidth, height: nameHeight }, { width: windowWidth, height: windowHeight })
	);
</script>

<svelte:window bind:innerWidth={windowWidth} bind:innerHeight={windowHeight} />

<!-- The part of the page the reader points at, ringed in the reader's colour as strong as a mark, its name on
	their chip beside it inside the window; nothing dimmed, and nothing of it in the way of the pointer -->
<div
	data-testid={testId}
	class="cr-ui-pointed"
	aria-hidden="true"
	style:--cr-pointed-left="{part.left}px"
	style:--cr-pointed-top="{part.top}px"
	style:--cr-pointed-width="{part.width}px"
	style:--cr-pointed-height="{part.height}px"
></div>
<span
	bind:offsetWidth={nameWidth}
	bind:offsetHeight={nameHeight}
	class="cr-ui-pointed-name"
	aria-hidden="true"
	style:--cr-pointed-name-left="{placed.left}px"
	style:--cr-pointed-name-top="{placed.top}px"
>
	<Chip voice="reader" names="part" onlyNames testId="{testId}-name">{part.name}</Chip>
</span>
