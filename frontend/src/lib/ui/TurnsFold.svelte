<script lang="ts">
	import type { Snippet } from 'svelte';
	import { wordsFor, type CountedWords } from '$lib/utils/words';
	import { BUTTON_SIZES } from './button';
	import FoldChevron from './FoldChevron.svelte';

	interface Props {
		/** How many turns it folds. */
		count: number;
		/** What the turns it folds are called, counted. */
		counts: CountedWords;
		/** Whether the reader opened it: the turns it folds stand under its row. */
		open: boolean;
		/** Called as the reader presses Show, or as the browser's find in page comes to words in the turns it folds. */
		onShow: () => void;
		onHide: () => void;
		testId: string;
		/** The turns it folds (Turn), with the rows nobody says between them (TurnAside). */
		children: Snippet;
	}

	let { count, counts, open, onShow, onHide, testId, children }: Props = $props();
</script>

<!-- Earlier turns of a conversation folded away, so a long one is not long: a row of the conversation, its one
	button standing on the spine as an avatar does, a rule across the rest of it; and under it the turns, which stay
	in the document hidden until found, so the browser's find in page reaches them and opens the fold as it does -->
<div data-testid={testId} class="cr-ui-turn-row cr-ui-turns-fold">
	<button
		type="button"
		data-testid="{testId}-toggle"
		class={['cr-ui-button cr-pressable', BUTTON_SIZES.xs, 'cr-ui-turns-fold-button']}
		aria-expanded={open}
		onclick={open ? onHide : onShow}
	>
		<FoldChevron folded={!open} />
		{#if open}Hide{:else}Show{/if}
		{count} earlier {wordsFor(count, counts)}
	</button>
	<span class="cr-ui-turns-fold-rule"></span>
</div>
<div
	data-testid="{testId}-held"
	class="cr-ui-turns-folded"
	hidden={open ? undefined : 'until-found'}
	onbeforematch={onShow}
>
	{@render children()}
</div>
