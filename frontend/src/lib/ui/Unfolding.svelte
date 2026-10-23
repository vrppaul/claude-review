<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/**
		 * Whether the reader opened it with a press just now: only then does it come down from under what heads
		 * it. Drawn open by anything else — the page drawn again, a way taken to what it holds — it stands at once.
		 */
		byReader: boolean;
		testId: string;
		/** What unfolds. */
		children: Snippet;
	}

	let { byReader, testId, children }: Props = $props();
</script>

<!-- What a fold opens, under what heads it, coming down over a fold's time where the reader opened it -->
<div data-testid={testId} class={[byReader && 'cr-ui-unfolding']}>{@render children()}</div>
