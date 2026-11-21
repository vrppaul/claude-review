<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * How its lines stand in their file:
	 * - picked: each apart from the next, where a name stands, a hairline between them
	 * - running: one after another, as the file reads round a place, drawn as a file's lines are
	 */
	type LinesRead = 'picked' | 'running';

	// The class of each in the library's stylesheet, over what every frame's lines have
	const READ_AS: Record<LinesRead, string | null> = { picked: null, running: 'cr-ui-code-frame-lines-running' };

	interface Props {
		reads: LinesRead;
		testId: string;
		/** Its rows, a line of the file to each. */
		children: Snippet;
	}

	let { reads, testId, children }: Props = $props();
</script>

<!-- Lines of one file, under its path in the frame (lib/ui/frame.ts): on the reading ground, each on a line of its
	own -->
<table data-testid={testId} class={['cr-ui-code-frame-lines', READ_AS[reads]]}>
	<tbody>
		{@render children()}
	</tbody>
</table>
