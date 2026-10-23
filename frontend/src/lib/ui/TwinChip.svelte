<script lang="ts">
	import Icon from './Icon.svelte';
	import type { TwinHalf } from './twin-chip';

	interface Props {
		/** Its counts, in the order they are read: one where the other has nothing to say. */
		halves: readonly TwinHalf[];
		testId: string;
	}

	let { halves, testId }: Props = $props();
</script>

<!-- How much a part holds, a half to each count (lib/ui/twin-chip.ts). Each count's words follow a space, so the
	counts are read apart, as the halves' gap parts them on the page, where that space draws nothing -->
<span data-testid={testId} class="cr-ui-twin-chip">
	{#each halves as half, place (place)}
		<span class="cr-ui-twin-chip-half"><Icon name={half.icon} size="xs" /> {half.words}</span>
	{/each}
</span>
