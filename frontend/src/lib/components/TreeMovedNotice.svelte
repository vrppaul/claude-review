<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import NoticeBar from '$lib/ui/NoticeBar.svelte';
	import { counted, FILES_HAVING } from '$lib/utils/words';
	import { Attempt } from './attempt.svelte';

	const review = useReview();
	const retaking = new Attempt();

	const moved = $derived(review.diff.treeMoved.count);
</script>

<!-- The warning's yellow, not the mark colour: this is the code moving, not
	the reader's own mark. Never a swap: whoever is mid-sentence decides when. -->
<NoticeBar tone="warning" icon="notice" testId="tree-moved">
	The working tree has moved on — {counted(moved, FILES_HAVING)} changed since this diff was taken.
	{#snippet actions()}
		{#if retaking.failed}
			<Failure stands="inline" testId="retake-error" said={retaking.failed} />
		{/if}
		<Button tone="quiet" size="xs" testId="retake-diff" onclick={() => retaking.run(() => review.diff.retake())}>
			Retake
		</Button>
		<Button tone="quiet" size="xs" testId="dismiss-moved" onclick={() => review.diff.treeMoved.dismiss()}>
			Dismiss
		</Button>
	{/snippet}
</NoticeBar>
