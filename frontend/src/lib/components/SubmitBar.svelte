<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';

	let submitting = $state(false);
	let error = $state<string | null>(null);
	let currentCommentIdx = $state(-1);

	async function handleSubmit() {
		if (commentStore.count === 0 || submitting) return;
		submitting = true;
		error = null;
		try {
			await commentStore.submit();
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

		// Switch to the file containing this comment
		diffStore.selectFile(comment.file);

		// Scroll to the comment element
		requestAnimationFrame(() => {
			const el = document.getElementById(comment.id);
			el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
		});
	}

	onMount(() => {
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
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
				<span class="text-sm text-base-content/60">
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
		<button
			class="btn btn-primary btn-sm"
			disabled={commentStore.count === 0 || submitting}
			onclick={handleSubmit}
		>
			{#if submitting}
				<span class="loading loading-spinner loading-xs"></span>
				Submitting...
			{:else}
				Submit Review (Ctrl+Shift+Enter)
			{/if}
		</button>
	</div>
{/if}
