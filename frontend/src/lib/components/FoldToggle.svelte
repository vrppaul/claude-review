<script lang="ts">
	import { FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';
	import Icon from './Icon.svelte';

	interface Props {
		folded: boolean;
		/** What folds, as whoever cannot see the chevron is told it: "this thread", a file's path. */
		subject: string;
		testId: string;
		onToggle: () => void;
	}

	let { folded, subject, testId, onToggle }: Props = $props();
</script>

<!-- One chevron for everything that folds: pointing down while open, right while folded -->
<button
	type="button"
	data-testid={testId}
	data-role={FOLD_TOGGLE_ROLE}
	class="btn btn-ghost btn-xs px-1"
	aria-expanded={!folded}
	aria-label={folded ? `Unfold ${subject}` : `Fold ${subject} away`}
	onclick={onToggle}
>
	<Icon name="chevron" class={['h-3 w-3 transition-transform', folded && '-rotate-90']} />
</button>
