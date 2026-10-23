<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/**
		 * Whether the reader opened it with a press just now: only then does it come down from under what heads
		 * it. Drawn open by anything else — the page drawn again, a way taken to what it holds — it stands at once.
		 */
		byReader: boolean;
		/** Whether it fades in as it comes down: a field the reader opens does; what a fold opens does not. */
		fading?: boolean;
		testId: string;
		/** What unfolds. */
		children: Snippet;
	}

	let { byReader, fading = false, testId, children }: Props = $props();
</script>

<!-- What a fold opens, under what heads it, or a field opened under what it is about, coming down over a fold's time
	where the reader opened it -->
<div data-testid={testId} class={[byReader && (fading ? 'cr-ui-unfolding-fading' : 'cr-ui-unfolding')]}>
	{@render children()}
</div>
