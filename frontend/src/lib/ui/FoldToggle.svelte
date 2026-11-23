<script lang="ts">
	import FoldChevron from './FoldChevron.svelte';
	import { foldToggleName } from './fold';
	import IconButton from './IconButton.svelte';

	interface Props {
		folded: boolean;
		/** What folds, as whoever cannot see the chevron is told it: "this thread", a file's path. */
		subject: string;
		/**
		 * What the page finds it by (its `data-role`): a thread's fold (`FOLD_TOGGLE_ROLE`), or what stands for a
		 * file's section (`STANDS_FOR_ITS_SECTION_ROLE`).
		 */
		role: string;
		testId: string;
		onToggle: () => void;
	}

	let { folded, subject, role, testId, onToggle }: Props = $props();
</script>

<!-- The toggle of a thread or a file, with the chevron everything that folds is drawn with -->
<IconButton
	tone="quiet"
	size="xs"
	shape="square"
	label={foldToggleName(folded, subject)}
	{testId}
	data-role={role}
	aria-expanded={!folded}
	onclick={onToggle}
>
	<FoldChevron {folded} />
</IconButton>
