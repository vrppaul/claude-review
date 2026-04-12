<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import ReviewModal from './ReviewModal.svelte';

	let submitting = $state(false);
	let error = $state<string | null>(null);
	let currentCommentIdx = $state(-1);
	let showModal = $state(false);

	async function handleSubmit() {
		if (!commentStore.hasContent || submitting) return;
		submitting = true;
		error = null;
		try {
			await commentStore.submit();
			showModal = false;
			window.close();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Submit failed';
		} finally {
			submitting = false;
		}
	}

	function navigateComment(direction: 1 | -1) {
		if (commentStore.count === 0) return;
		currentCommentIdx = (currentCommentIdx + direction + commentStore.count) % commentStore.count;
		const comment = commentStore.comments[currentCommentIdx];

		diffStore.selectFile(comment.file);

		requestAnimationFrame(() => {
			const el = document.getElementById(comment.id);
			el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
		});
	}

	onMount(() => {
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
				if (showModal) return; // modal handles its own shortcut
				if (commentStore.count === 0) return; // match button disabled state
				e.preventDefault();
				handleSubmit();
			}
		}
		window.addEventListener('keydown', onKeydown);
		return () => window.removeEventListener('keydown', onKeydown);
	});
</script>

{#if commentStore.submitted}
	<div class="fixed bottom-0 left-0 right-0 bg-success text-success-content p-4 text-center z-50">
		<p class="font-semibold">Review submitted. You can close this tab.</p>
	</div>
{:else}
	<div
		class="fixed bottom-0 left-0 right-0 bg-base-100 border-t border-base-300 px-4 py-3 flex items-center justify-between z-50"
	>
		<div class="flex items-center gap-2">
			{#if error}
				<span class="text-sm text-error">{error}</span>
			{:else}
				<span data-testid="comment-count" class="text-sm text-base-content/60">
					{commentStore.count}
					{commentStore.count === 1 ? 'comment' : 'comments'}
				</span>
			{/if}
			{#if commentStore.count > 0}
				<div class="flex gap-0.5">
					<button class="btn btn-ghost btn-xs" onclick={() => navigateComment(-1)} title="Previous comment">
						&#9650;
					</button>
					<button class="btn btn-ghost btn-xs" onclick={() => navigateComment(1)} title="Next comment">
						&#9660;
					</button>
				</div>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<button
				class="btn btn-primary btn-sm"
				data-testid="finish-review"
				onclick={() => (showModal = true)}
			>
				Finish review
			</button>
			<button
				class="btn btn-success btn-sm"
				data-testid="quick-submit"
				disabled={commentStore.count === 0 || submitting}
				onclick={handleSubmit}
			>
				{#if submitting}
					<span class="loading loading-spinner loading-xs"></span>
					Submitting...
				{:else}
					Quick submit (Ctrl+Shift+Enter)
				{/if}
			</button>
		</div>
	</div>

	{#if showModal}
		<ReviewModal
			onSubmit={handleSubmit}
			onClose={() => (showModal = false)}
		/>
	{/if}
{/if}
