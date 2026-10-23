<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		testId: string;
		children: Snippet;
	}

	let { testId, children }: Props = $props();
</script>

<!-- A warning set apart by a line down its start, in the warning's colour, on its tint (lib/ui/frame.ts) -->
<div data-testid={testId} class="cr-ui-edge-frame">
	{@render children()}
</div>
