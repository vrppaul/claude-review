<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';
	import FoldChevron from './FoldChevron.svelte';

	// How a toggle is drawn unless what it stands among draws its own controls otherwise: a plain small button
	const PLAIN_TOGGLE = 'btn btn-ghost btn-xs px-1';

	interface Props {
		folded: boolean;
		/** What folds, as whoever cannot see the chevron is told it: "this thread", a file's path. */
		subject: string;
		testId: string;
		/** How it is drawn, where the controls beside it have a look of their own. */
		class?: ClassValue;
		onToggle: () => void;
	}

	let { folded, subject, testId, class: look = PLAIN_TOGGLE, onToggle }: Props = $props();
</script>

<!-- The toggle of a thread or a file, with the chevron everything that folds is drawn with -->
<button
	type="button"
	data-testid={testId}
	data-role={FOLD_TOGGLE_ROLE}
	class={look}
	aria-expanded={!folded}
	aria-label={folded ? `Unfold ${subject}` : `Fold ${subject} away`}
	onclick={onToggle}
>
	<FoldChevron {folded} class="h-3 w-3" />
</button>
