<script lang="ts">
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import Icon from './Icon.svelte';

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children' | 'aria-label' | 'title'> {
		/** What pressing it does, in words: said to whoever cannot see its chevron, and shown under the pointer. */
		label: string;
		testId: string;
		/** The rail itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
	}

	let { label, testId, element = $bindable(), ...attributes }: Props = $props();
</script>

<!-- What a column put away leaves where it stood: one press, anywhere down it, brings the column back. The
	columns that are put away stand on the left, so its chevron points the way the column comes back in -->
<button
	bind:this={element}
	type="button"
	{...attributes}
	aria-label={label}
	title={label}
	data-testid={testId}
	class="cr-ui-column-rail cr-pressable"
>
	<Icon name="chevron" size="xs" pointing="right" />
</button>
