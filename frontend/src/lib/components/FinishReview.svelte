<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { scrollToComment } from '$lib/utils/scroll';

	interface Props {
		submitting: boolean;
		onSendRound: () => void;
		onSubmit: () => void;
		onEnd: () => void;
		onClose: () => void;
	}

	let { submitting, onSendRound, onSubmit, onEnd, onClose }: Props = $props();

	let summary = $state<HTMLTextAreaElement | null>(null);

	// A round is only worth offering while something is there to work through
	// it; on its own, sending is the end of the review
	const inRounds = $derived(reviewStore.canSendRound);
	const unsent = $derived(commentStore.unsentCount);

	onMount(() => summary?.focus());

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault();
			onClose();
		}
		if (event.key === 'Enter' && (event.metaKey || event.ctrlKey) && event.shiftKey) {
			event.preventDefault();
			// The same rule as the button it stands for: nothing written,
			// nothing sent
			if (inRounds && commentStore.hasUnsent) onSendRound();
			else if (!inRounds && commentStore.hasContent) onSubmit();
		}
	}

	function jump(id: string, file: string) {
		onClose();
		scrollToComment(id, file);
	}
</script>

<svelte:window onkeydown={onKeydown} />

<!-- Click anywhere else and the review carries on where it was -->
<button
	data-testid="finish-backdrop"
	class="fixed inset-0 z-40 cursor-default"
	aria-label="Close"
	onclick={onClose}
></button>

<div
	data-testid="finish-review"
	role="dialog"
	aria-modal="false"
	aria-label="Finish the review"
	class="cr-popover absolute right-3 top-12 z-50 flex max-h-[70vh] w-[26rem] flex-col"
>
	<div class="flex items-baseline gap-2 border-b border-base-300 px-4 py-2.5">
		<h3 class="text-sm font-semibold">
			{inRounds ? `Round ${reviewStore.round}` : 'Finish the review'}
		</h3>
		<span data-testid="finish-count" class="cr-faint text-xs">
			{#if inRounds}
				{unsent} unsent of {commentStore.count}
			{:else}
				{commentStore.count}
				{commentStore.count === 1 ? 'comment' : 'comments'}
			{/if}
		</span>
	</div>

	<div class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
		{#if commentStore.count === 0}
			<p class="cr-faint text-sm">
				Nothing written yet. A summary on its own is a review too.
			</p>
		{:else}
			<ul class="flex flex-col gap-1.5">
				{#each commentStore.comments as comment (comment.id)}
					{@const sent = commentStore.sentInRound(comment.id)}
					<li>
						<button
							data-testid="finish-comment"
							class="cr-finish-row w-full rounded px-2 py-1.5 text-left {sent !== undefined
								? 'opacity-55'
								: ''}"
							onclick={() => jump(comment.id, comment.file)}
						>
							<span class="flex items-baseline gap-2">
								<span data-testid="modal-comment-ref" class="cr-comment-ref font-mono text-xs">
									{comment.file} · {lineRangeLabel(
										comment.side,
										comment.start_line,
										comment.end_line
									)}
								</span>
								{#if comment.severity !== 'note'}
									<span class="cr-severity cr-severity-{comment.severity}">{comment.severity}</span>
								{/if}
								{#if comment.raised_by === 'author'}
									<span class="cr-severity cr-raised-tag">author</span>
								{/if}
								{#if comment.resolved}
									<span class="cr-severity cr-muted">resolved</span>
								{/if}
								<span class="flex-1"></span>
								{#if sent !== undefined}
									<span class="cr-faint shrink-0 text-xs">round {sent}</span>
								{/if}
							</span>
							<span class="cr-comment-body mt-0.5 block whitespace-pre-wrap">{comment.body}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<div class="border-t border-base-300 px-4 py-3">
		<textarea
			bind:this={summary}
			data-testid="review-body"
			class="cr-field cr-comment-body min-h-16 w-full rounded px-3 py-2"
			placeholder="Summary — optional, about the change as a whole"
			value={commentStore.reviewBody}
			oninput={(e) => commentStore.setReviewBody(e.currentTarget.value)}
		></textarea>

		<div class="mt-2 flex items-center gap-2">
			<span class="cr-faint hidden text-xs lg:inline">Ctrl+Shift+Enter sends</span>
			<div class="flex-1"></div>
			{#if inRounds}
				<button data-testid="end-review" class="btn btn-ghost btn-sm" onclick={onEnd}>
					End review
				</button>
				<button
					data-testid="modal-submit"
					class="btn btn-primary btn-sm"
					disabled={!commentStore.hasUnsent || submitting}
					onclick={onSendRound}
				>
					{submitting ? 'Sending' : `Send round ${reviewStore.round}`}
				</button>
			{:else}
				<button
					data-testid="modal-submit"
					class="btn btn-primary btn-sm"
					disabled={!commentStore.hasContent || submitting}
					onclick={onSubmit}
				>
					{submitting ? 'Sending' : 'Send review'}
				</button>
			{/if}
		</div>
	</div>
</div>
