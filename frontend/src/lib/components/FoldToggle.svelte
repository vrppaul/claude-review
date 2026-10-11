<script lang="ts">
	import Icon from './Icon.svelte';

	interface Props {
		folded: boolean;
		/** What folding does, said to whoever cannot see the chevron: "Fold this thread away". */
		foldLabel: string;
		/** What unfolding does: "Unfold this thread". */
		unfoldLabel: string;
		testId: string;
		onToggle: () => void;
	}

	let { folded, foldLabel, unfoldLabel, testId, onToggle }: Props = $props();
</script>

<!-- One chevron for everything that folds: pointing down while open, right while folded -->
<button
	type="button"
	data-testid={testId}
	class="btn btn-ghost btn-xs px-1"
	aria-expanded={!folded}
	aria-label={folded ? unfoldLabel : foldLabel}
	onclick={onToggle}
>
	<Icon name="chevron" class={['h-3 w-3 transition-transform', folded && '-rotate-90']} />
</button>
