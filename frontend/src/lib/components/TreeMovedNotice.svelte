<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import { counted, FILES_HAVING } from '$lib/utils/words';
	import { Attempt } from './attempt.svelte';
	import NoticeBar from './NoticeBar.svelte';

	const review = useReview();
	const retaking = new Attempt();

	const moved = $derived(review.diff.treeMoved.count);
</script>

<!-- The warning's yellow, not the mark colour: this is the code moving, not
	the reader's own mark. Never a swap: whoever is mid-sentence decides when. -->
<NoticeBar testId="tree-moved" kind="cr-notice-moved" icon="notice">
	The working tree has moved on — {counted(moved, FILES_HAVING)} changed since this diff was taken.
	{#snippet actions()}
		{#if retaking.failed}
			<span data-testid="retake-error" class="text-error">{retaking.failed}</span>
		{/if}
		<Button tone="quiet" size="xs" data-testid="retake-diff" onclick={() => retaking.run(() => review.diff.retake())}>
			Retake
		</Button>
		<Button tone="quiet" size="xs" data-testid="dismiss-moved" onclick={() => review.diff.treeMoved.dismiss()}>
			Dismiss
		</Button>
	{/snippet}
</NoticeBar>
