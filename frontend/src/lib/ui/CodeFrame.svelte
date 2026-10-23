<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** What it frames: what heads the code, its file's bar and its lines. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- Code set apart in a frame of its own, edged as a pane and rounded (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-code-frame">
	{@render children()}
</div>
