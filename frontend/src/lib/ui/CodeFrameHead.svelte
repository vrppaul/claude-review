<script lang="ts">
	import type { Snippet } from 'svelte';
	import Avatar from './Avatar.svelte';

	interface Props {
		testId: string;
		/** What heads the code: what the agent says of it. */
		children: Snippet;
		/** What stands at the line's end: the act on what it says, where it may be asked about. */
		end?: Snippet | undefined;
	}

	let { testId, children, end }: Props = $props();
</script>

<!-- The top line of a frame of code: what the agent says heads the code, after its avatar (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-code-frame-head">
	<Avatar speaker="agent" />
	{@render children()}
	{#if end}
		<span class="cr-ui-code-frame-head-end">{@render end()}</span>
	{/if}
</div>
