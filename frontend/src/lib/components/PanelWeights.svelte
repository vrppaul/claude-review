<script lang="ts">
	import { formatWeight } from '$lib/review/weight';
	import { useReview } from '$lib/review/context';
	import Tag from '$lib/ui/Tag.svelte';
	import { timeAgo } from '$lib/utils/time';

	const review = useReview();

	/** How long ago the agent reported its context, if it ever has. */
	function reportedAgo(at: number | null): string {
		return at === null ? '' : timeAgo(at, review.clock.now);
	}
</script>

<!-- Two numbers, told apart: one this side measures, one the agent reports -->
<div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-base-300 px-3 py-1.5">
	<Tag tone="quiet" testId="review-weight" title="What handing this review over costs">
		review {formatWeight(review.weight)} tokens
	</Tag>
	{#if review.answerer.status.context}
		<Tag tone="quiet" testId="agent-context">
			context {review.answerer.status.context} · as reported {reportedAgo(review.answerer.status.at)}
		</Tag>
	{/if}
</div>
