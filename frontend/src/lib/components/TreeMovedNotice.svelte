<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { counted } from '$lib/utils/words';
	import { Attempt } from './attempt.svelte';
	import Icon from './Icon.svelte';

	const review = useReview();
	const retaking = new Attempt();

	const moved = $derived(review.diff.treeMoved.count);
</script>

<!-- The warning's yellow, not the mark colour: this is the code moving, not
	the reader's own mark. Never a swap: whoever is mid-sentence decides when. -->
<div
	data-testid="tree-moved"
	class="cr-notice cr-notice-moved flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
>
	<Icon name="notice" class="h-3 w-3 shrink-0" />
	<span>
		The working tree has moved on — {counted(moved, 'file has', 'files have')} changed since this diff was taken.
	</span>
	<div class="flex-1"></div>
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
</div>
