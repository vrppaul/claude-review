<script lang="ts">
	import type { Snippet } from 'svelte';
	import { REPLIES, wordsFor } from '$lib/utils/words';
	import Button from './Button.svelte';
	import FoldChevron from './FoldChevron.svelte';
	import TurnAside from './TurnAside.svelte';

	interface Props {
		/** How many turns it folds. */
		count: number;
		/** Whether the reader opened it: the turns it folds stand under its row. */
		open: boolean;
		/** Called as the reader presses Show, or as the browser's find in page comes to words in the turns it folds. */
		onShow: () => void;
		onHide: () => void;
		testId: string;
		/** The turns it folds (Turn), with the rows nobody says between them (TurnAside). */
		children: Snippet;
	}

	let { count, open, onShow, onHide, testId, children }: Props = $props();
</script>

<!-- Earlier turns of a conversation folded away, so a long one is not long: a row of the conversation, its one
	button standing on the spine; and under it the turns, which stay in the document hidden until found, so the
	browser's find in page reaches them and opens the fold as it does -->
<TurnAside lays="on-the-spine" {testId}>
	<Button tone="folded-away" size="xs" testId="{testId}-toggle" aria-expanded={open} onclick={open ? onHide : onShow}>
		<FoldChevron folded={!open} />
		{#if open}Hide{:else}Show{/if}
		{count} earlier {wordsFor(count, REPLIES)}
	</Button>
</TurnAside>
<div
	data-testid="{testId}-held"
	class="cr-ui-turns-folded"
	hidden={open ? undefined : 'until-found'}
	onbeforematch={onShow}
>
	{@render children()}
</div>
