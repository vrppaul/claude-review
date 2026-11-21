<script lang="ts">
	interface Props {
		/** The file the lines under it are of. */
		path: string;
		testId: string;
	}

	let { path, testId }: Props = $props();
</script>

<!-- The top line of a frame of lines picked out of one file: its path, cut where the room ends (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-code-frame-path">{path}</div>
