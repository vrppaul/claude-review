<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** Its rows: turns (Turn) and rows nobody says (TurnAside); or the parts of a comment being written, as the thread it becomes. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- A conversation, a thread's or the panel's with the agent: its rows one under another, as far apart as the
	pieces of the spine each draws reach, so the spine runs unbroken from the first avatar to the last -->
<div data-testid={testId} class="cr-ui-conversation">
	{@render children()}
</div>
