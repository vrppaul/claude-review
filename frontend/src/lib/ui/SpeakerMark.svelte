<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Voice } from './voice';
	import Avatar from './Avatar.svelte';

	interface Props {
		speaker: Voice;
		/** What stands on its corner, ringed in the ground round it: whether the agent is there, at work or listening. */
		corner?: Snippet | undefined;
	}

	let { speaker, corner }: Props = $props();
</script>

<!-- Who is behind what is put away, as a turn names who said it: their avatar at a turn's size, on a column's rail,
	what is said of them on its corner -->
<span class="cr-ui-speaker-mark">
	<Avatar {speaker} />
	{#if corner}
		<span class="cr-ui-speaker-mark-corner">{@render corner()}</span>
	{/if}
</span>
