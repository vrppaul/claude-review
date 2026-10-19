<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	interface Props extends Omit<HTMLInputAttributes, 'class' | 'style' | 'type' | 'value' | 'children' | 'aria-label'> {
		/** What it narrows, said to whoever cannot see the list beside it: "Filter the bases". */
		label: string;
		testId: string;
		/** What the reader typed into it. */
		value?: string;
	}

	let { label, testId, value = $bindable(), ...attributes }: Props = $props();
</script>

<!-- A field that narrows the list it heads to what answers to the words typed into it: in the code's face, as
	the paths and names it is matched against are, and edged as every field the reader fills is (lib/ui/field.ts) -->
<input
	type="search"
	bind:value
	{...attributes}
	aria-label={label}
	data-testid={testId}
	class="cr-ui-field cr-ui-filter"
/>
