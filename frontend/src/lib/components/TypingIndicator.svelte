<script lang="ts">
	import type { DotTone } from '$lib/ui/dot';
	import Dot from '$lib/ui/Dot.svelte';

	interface Props {
		/**
		 * Whether the dots breathe in the agent's colour, as the words beside them are said in it: on Story while
		 * the agent writes the story. Elsewhere they breathe quietly, beside words that say whose turn it is.
		 */
		inTheAgentsColour?: boolean;
	}

	let { inTheAgentsColour = false }: Props = $props();

	const tone = $derived<DotTone>(inTheAgentsColour ? 'agent' : 'quiet');
</script>

<!-- Three dots that breathe in turn while an answer is on its way: a line that never changes reads as a hang.
	Unsaid to a screen reader, as every dot is — the words beside them say what is waited on. -->
<span data-testid="breathing-dots" class="flex items-center gap-1">
	<Dot {tone} breathing testId="breathing-dot" />
	<Dot {tone} breathing testId="breathing-dot" />
	<Dot {tone} breathing testId="breathing-dot" />
</span>
