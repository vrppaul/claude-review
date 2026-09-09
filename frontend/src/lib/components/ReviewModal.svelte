<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';

	interface Props {
		onSubmit: () => void;
		onClose: () => void;
	}

	let { onSubmit, onClose }: Props = $props();

	let textareaEl: HTMLTextAreaElement;

	onMount(() => {
		textareaEl?.focus();
	});

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onClose();
		}
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
			e.preventDefault();
			onSubmit();
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		// Only close when clicking the backdrop itself, not the modal content
		if (e.target === e.currentTarget) {
			onClose();
		}
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
	role="dialog"
	aria-modal="true"
	aria-labelledby="review-modal-title"
	tabindex="-1"
	class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
	onkeydown={handleKeydown}
	onclick={handleBackdropClick}
>
	<div class="cr-dialog flex max-h-[80vh] w-full max-w-xl flex-col rounded-lg bg-base-100">
		<div class="border-b border-base-300 px-6 py-4">
			<h3 id="review-modal-title" class="text-lg font-semibold">Review summary</h3>
		</div>

		<div class="flex-1 space-y-5 overflow-y-auto px-6 py-4">
			<div>
				<h4 class="cr-muted mb-2 text-sm font-semibold">
					General feedback, not tied to a line
				</h4>
				<textarea
					bind:this={textareaEl}
					data-testid="review-body"
					class="cr-comment-body textarea min-h-24 w-full bg-base-100 focus:outline-none"
					placeholder="What should Claude know about the change as a whole?"
					value={commentStore.reviewBody}
					oninput={(e) => commentStore.setReviewBody(e.currentTarget.value)}
				></textarea>
			</div>

			{#if commentStore.count > 0}
				<div>
					<h4 class="cr-muted mb-2 text-sm font-semibold">
						{commentStore.count} inline {commentStore.count === 1 ? 'comment' : 'comments'}
					</h4>
					<ul class="space-y-2">
						{#each commentStore.comments as comment (comment.id)}
							<li class="rounded bg-base-200 px-3 py-2">
								<div data-testid="modal-comment-ref" class="cr-comment-ref font-mono text-xs">
									{comment.file} · {lineRangeLabel(
										comment.side,
										comment.start_line,
										comment.end_line
									)}
								</div>
								<p class="cr-comment-body mt-1 whitespace-pre-wrap">{comment.body}</p>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>

		<div class="flex items-center gap-2 border-t border-base-300 px-6 py-4">
			<span class="cr-muted text-xs">Ctrl+Shift+Enter to send</span>
			<div class="flex-1"></div>
			<button class="btn btn-ghost btn-sm" data-testid="cancel-modal" onclick={onClose}>
				Keep reviewing
			</button>
			<button
				class="btn btn-primary btn-sm"
				data-testid="modal-submit"
				disabled={!commentStore.hasContent}
				onclick={onSubmit}
			>
				Send to Claude
			</button>
		</div>
	</div>
</div>
