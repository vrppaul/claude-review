<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** What stands where the code would: the step's number, and what is said in place of its code. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- A row of a frame of code where no code is drawn, as tall as a file's bar (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-code-frame-row">
	{@render children()}
</div>
