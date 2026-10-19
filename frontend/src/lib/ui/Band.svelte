<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		/** Whether it is the one the reader is at: something of theirs hangs open under it. */
		current: boolean;
		testId: string;
		/** What it holds: what heads it, and its words. */
		children: Snippet;
		/** What it offers over its top right edge while it is pointed at or holds the keyboard: the act on what it holds. */
		offer: Snippet;
	}

	let { current, testId, children, offer }: Props = $props();
</script>

<!-- A block lit across the frame of bands it stands in, from inside the frame's edge to its far side
	(lib/ui/frame.ts): by the pointer's light while pointed at or holding the keyboard, on the reader's mark while
	it is the one they are at; offering its act over its top right edge while lit -->
<div data-testid={testId} class={['cr-ui-band', current && 'cr-ui-band-current']}>
	{@render children()}
	<span class="cr-ui-band-offer">{@render offer()}</span>
</div>
