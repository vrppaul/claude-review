<script lang="ts">
	import { FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';
	import FoldChevron from './FoldChevron.svelte';

	interface Props {
		folded: boolean;
		/** What folds, as whoever cannot see the chevron is told it: "this thread", a file's path. */
		subject: string;
		testId: string;
		onToggle: () => void;
	}

	let { folded, subject, testId, onToggle }: Props = $props();
</script>

<!-- The toggle of a thread or a file, with the chevron everything that folds is drawn with -->
<button
	type="button"
	data-testid={testId}
	data-role={FOLD_TOGGLE_ROLE}
	class="btn btn-ghost btn-xs px-1"
	aria-expanded={!folded}
	aria-label={folded ? `Unfold ${subject}` : `Fold ${subject} away`}
	onclick={onToggle}
>
	<FoldChevron {folded} class="h-3 w-3" />
</button>
