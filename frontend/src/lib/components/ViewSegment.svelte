<script lang="ts">
	import Icon from './Icon.svelte';
	import TypingIndicator from './TypingIndicator.svelte';
	import type { Offered, Said } from './view-segments';

	interface Props {
		/** The way of reading the review this segment offers. */
		offered: Offered;
		/** Whether that is how the review is read now. */
		onScreen: boolean;
		/** What it says of its view beyond the view's name. */
		says: Said;
		onPress: () => void;
		/** The segment itself, held by the switch, which hands it the keyboard and stands a note under it. */
		segment?: HTMLElement | undefined;
	}

	// The class a segment carries for what it says beyond its name
	const SAID_WITH: Record<Said, string | null> = {
		nothing: null,
		writing: 'cr-segment-writing',
		unread: 'cr-segment-unread'
	};

	let { offered, onScreen, says, onPress, segment = $bindable() }: Props = $props();
</script>

<!-- One segment of the header's switch: a way to read the review, pressed while it is the one on screen.
	While the agent writes what its view will show, dots that breathe stand for its icon -->
<button
	bind:this={segment}
	type="button"
	data-testid={offered.testId}
	class={['cr-segment flex items-center gap-1.5', SAID_WITH[says]]}
	aria-pressed={onScreen}
	onclick={onPress}
>
	{#if says === 'writing'}
		<TypingIndicator />
		{offered.label} · writing
	{:else}
		<Icon name={offered.icon} class="h-3.5 w-3.5" />
		{offered.label}
	{/if}
	{#if says === 'unread'}
		<!-- Unsaid to a screen reader: the note under the switch said it -->
		<span data-testid="segment-unread" class="text-(--cr-unread)" aria-hidden="true">●</span>
	{/if}
</button>
