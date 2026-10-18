<script lang="ts">
	interface Props {
		/**
		 * Whether the dots breathe in the agent's colour, as the words beside them are said in it: on Story while
		 * the agent writes the story. Elsewhere they breathe quietly, beside words that say whose turn it is.
		 */
		inTheAgentsColour?: boolean;
	}

	let { inTheAgentsColour = false }: Props = $props();

	const dotClasses = $derived(['cr-dot', inTheAgentsColour && 'cr-dot-agent']);
</script>

<!-- Three dots that breathe while an answer is on its way: a line that never
	changes reads as a hang. Unsaid to a screen reader — the words beside it
	say what is waited on. -->
<span data-testid="breathing-dots" class="flex items-center gap-1" aria-hidden="true">
	<span class={dotClasses}></span><span class={dotClasses}></span><span class={dotClasses}></span>
</span>
