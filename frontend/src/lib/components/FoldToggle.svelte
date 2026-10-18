<script lang="ts">
	import { FOLD_TOGGLE_ROLE } from '$lib/dom/file-sections';
	import IconButton from '$lib/ui/IconButton.svelte';
	import FoldChevron from './FoldChevron.svelte';

	interface Props {
		folded: boolean;
		/** What folds, as whoever cannot see the chevron is told it: "this thread", a file's path. */
		subject: string;
		testId: string;
		/**
		 * What it is beside the controls it stands among: quiet on a file's header; secondary among a thread's
		 * buttons, which act on the thread and are edged so.
		 */
		tone: 'quiet' | 'secondary';
		onToggle: () => void;
	}

	let { folded, subject, testId, tone, onToggle }: Props = $props();
</script>

<!-- The toggle of a thread or a file, with the chevron everything that folds is drawn with -->
<IconButton
	{tone}
	size="xs"
	label={folded ? `Unfold ${subject}` : `Fold ${subject} away`}
	{testId}
	data-role={FOLD_TOGGLE_ROLE}
	aria-expanded={!folded}
	onclick={onToggle}
>
	<FoldChevron {folded} />
</IconButton>
