<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';

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

	function truncate(text: string, max: number): string {
		return text.length > max ? text.slice(0, max) + '...' : text;
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
	class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]"
	onkeydown={handleKeydown}
	onclick={handleBackdropClick}
>
	<div class="bg-base-100 rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
		<div class="px-6 py-4 border-b border-base-300">
			<h3 id="review-modal-title" class="text-lg font-semibold">Submit Review</h3>
		</div>

		<div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
			{#if commentStore.count > 0}
				<div>
					<h4 class="text-sm font-semibold text-base-content/60 mb-2">
						{commentStore.count} inline {commentStore.count === 1 ? 'comment' : 'comments'}
					</h4>
					<ul class="space-y-1">
						{#each commentStore.comments as comment (comment.id)}
							<li class="text-xs font-mono bg-base-200 rounded px-3 py-2">
								<span class="text-info">{comment.file}:{comment.start_line}{comment.start_line !== comment.end_line ? `-${comment.end_line}` : ''}</span>
								<span class="text-base-content/60 ml-2">{truncate(comment.body, 80)}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/if}

			<div>
				<h4 class="text-sm font-semibold text-base-content/60 mb-2">Review summary</h4>
				<textarea
					bind:this={textareaEl}
					class="textarea textarea-bordered w-full text-sm min-h-24 focus:outline-none focus:border-info"
					placeholder="General feedback — not tied to a specific line (optional)"
					value={commentStore.reviewBody}
					oninput={(e) => commentStore.setReviewBody(e.currentTarget.value)}
				></textarea>
			</div>
		</div>

		<div class="px-6 py-4 border-t border-base-300 flex justify-end gap-2">
			<button class="btn btn-ghost btn-sm" onclick={onClose}>
				Cancel
			</button>
			<button
				class="btn btn-success btn-sm"
				disabled={!commentStore.hasContent}
				onclick={onSubmit}
			>
				Submit review (Ctrl+Shift+Enter)
			</button>
		</div>
	</div>
</div>
