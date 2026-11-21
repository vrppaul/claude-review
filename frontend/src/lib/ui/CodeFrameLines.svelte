<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		/** Its rows, a line of the file to each. */
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- Lines picked out of one file, under its path in the frame (lib/ui/frame.ts): on the reading ground, each on a
	line of its own, a hairline between them -->
<table data-testid={testId} class="cr-ui-code-frame-lines">
	<tbody>
		{@render children()}
	</tbody>
</table>
