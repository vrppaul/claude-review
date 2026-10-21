<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { COLUMN_SIDES, type ColumnSide } from './column';
	import Icon from './Icon.svelte';

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children' | 'aria-label' | 'title'> {
		side: ColumnSide;
		/** What pressing it does, in words: said to whoever cannot see its toggle, and shown under the pointer. */
		label: string;
		/** The key that does the same, shown under the pointer after the words: `f`. */
		key: string;
		testId: string;
		/** The rail itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
		/** What is behind it, said under its head: a count, the chapter being read, who is there. */
		marks?: Snippet | undefined;
		/** Whether its marks come in once the column has narrowed: so where the reader put the column away. */
		marksComeIn: boolean;
	}

	let { side, label, key, testId, element = $bindable(), marks, marksComeIn, ...attributes }: Props = $props();
</script>

<!-- What a column put away leaves where it stood, the column narrowed: its head the column's own height, the toggle
	drawn on the spot it stood on in the open column's head, and under it what is behind it. One press, anywhere down
	it, brings the column back -->
<button
	bind:this={element}
	type="button"
	{...attributes}
	aria-label={label}
	title="{label} ({key})"
	data-testid={testId}
	class="cr-ui-column-rail cr-pressable"
>
	<span class="cr-ui-column-rail-head"><Icon name={COLUMN_SIDES[side].putAway} size="sm" /></span>
	{#if marks}
		<span class={['cr-ui-column-rail-marks', marksComeIn && 'cr-ui-column-rail-marks-coming']}>{@render marks()}</span>
	{/if}
</button>
