<script lang="ts">
	interface Props {
		/** The file the lines under it are of. */
		path: string;
		/** What the lines stand inside in the file, a class or a function, where it is known: said after the path. */
		within?: string | null;
		/** What it says at its end of where the lines stand: whether the change holds their file. */
		said?: string | undefined;
		testId: string;
	}

	let { path, within = null, said, testId }: Props = $props();
</script>

<!-- The top line of a frame of lines picked out of one file: its path, and what the lines stand inside, cut where
	the room ends, and at its end what it says of them (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-code-frame-path">
	<span class="cr-ui-code-frame-path-where"
		>{path}{#if within !== null}, in {within}{/if}</span
	>
	{#if said !== undefined}
		<span class="cr-ui-code-frame-path-said">{said}</span>
	{/if}
</div>
