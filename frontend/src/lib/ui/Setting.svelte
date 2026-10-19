<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** What the setting is called: "Theme". */
		label: string;
		testId: string;
		/** Its control, at the far end of the line: a track of segments. */
		children: Snippet;
	}

	let { label, testId, children }: Props = $props();
</script>

<!-- A setting of a pane, as every one is laid out, a box ticked or not too (Checkbox): what it is called first, and
	its control at the far end of the line -->
<div data-testid={testId} class="cr-ui-setting">
	<span>{label}</span>
	{@render children()}
</div>
