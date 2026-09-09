<script lang="ts">
	import { onMount } from 'svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import ReviewModal from './ReviewModal.svelte';
	import TopBar from './TopBar.svelte';

	let submitting = $state(false);
	let error = $state<string | null>(null);
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
			error = e instanceof Error ? e.message : 'Could not send the review';
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
				if (showModal) return; // the modal handles its own shortcut
				if (!commentStore.hasContent) return; // match the button's disabled state
				e.preventDefault();
				handleSubmit();
			}
		}
		window.addEventListener('keydown', onKeydown);
		return () => window.removeEventListener('keydown', onKeydown);
	});
</script>

{#if commentStore.submitted}
	<div
		data-testid="submitted-banner"
		class="flex h-12 shrink-0 items-center justify-center gap-3 border-b border-base-300 bg-base-200 px-4"
	>
		<svg class="h-4 w-4" viewBox="0 0 12 12" fill="currentColor" style="color: var(--cr-mark)"
			aria-hidden="true"><path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" /></svg>
		<p class="font-semibold">Review sent. You can close this tab.</p>
	</div>
{:else}
	<TopBar {submitting} {error} onSubmit={handleSubmit} onOpenModal={() => (showModal = true)} />

	{#if showModal}
		<ReviewModal onSubmit={handleSubmit} onClose={() => (showModal = false)} />
	{/if}
{/if}
