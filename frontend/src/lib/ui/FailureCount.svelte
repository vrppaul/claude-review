<script lang="ts">
	import Icon from './Icon.svelte';

	interface Props {
		/** How many places something failed in what it stands beside. */
		count: number;
		/** Whether the code changed after every one of them was found: stepped back to ink. */
		outOfDate: boolean;
		/** What the mark says in words, on the pointer and to whoever cannot see it. */
		label: string;
		testId: string;
	}

	let { count, outOfDate, label, testId }: Props = $props();
</script>

<!-- A mark of how many places failed: the error's cross and a figure, said in words to a screen reader. A kind of its
	own, not a Count: a Count is a figure alone in a tag's box, and this is a mark and a figure on the row's ground -->

<span
	data-testid={testId}
	title={label}
	class={['cr-ui-failure-count', outOfDate && 'cr-ui-failure-count-out-of-date']}
>
	<Icon name="cross" size="xs" />
	<span aria-hidden="true">{count}</span>
	<span class="sr-only">{label}</span>
</span>
