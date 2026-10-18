<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	/** What draws the reader to a segment: what the agent brought there and they have not read, or the way of reading the page introduces. */
	type Calling = 'unread' | 'introduced';

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children' | 'aria-pressed'> {
		/** Whether it is the one picked. */
		pressed: boolean;
		/** Whether the agent is writing what it picks: said in the agent's colour. */
		written?: boolean;
		calling?: Calling | undefined;
		testId: string;
		/** The segment itself, for whoever hands the keyboard to it or points at it. */
		element?: HTMLButtonElement | undefined;
		/** What it says: its words, an icon before them. */
		children: Snippet;
	}

	let { pressed, written = false, calling, testId, element = $bindable(), children, ...attributes }: Props = $props();
</script>

<!-- A segment of a track: one way of reading, pressed while it is the one picked, and saying what draws the
	reader to it, which the stylesheet edges it by -->
<button
	bind:this={element}
	type="button"
	{...attributes}
	aria-pressed={pressed}
	data-calling={calling}
	data-testid={testId}
	class={['cr-ui-segment cr-pressable', written && 'cr-ui-segment-written']}
>
	{@render children()}
</button>
