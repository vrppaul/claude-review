<script lang="ts">
	import { useReview } from '$lib/review/context';
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
		<button
			type="button"
			data-testid="retake-diff"
			class="btn btn-ghost btn-xs"
			onclick={() => retaking.run(() => review.diff.retake())}
		>
			Retake
		</button>
		<button
			type="button"
			data-testid="dismiss-moved"
			class="btn btn-ghost btn-xs"
			onclick={() => review.diff.treeMoved.dismiss()}
		>
			Dismiss
		</button>
	{/snippet}
</NoticeBar>
