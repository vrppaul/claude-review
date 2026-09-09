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
				if (commentStore.count === 0) return; // match the button's disabled state
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
		class="flex h-12 shrink-0 items-center justify-center border-b border-base-300 bg-success px-4 text-success-content"
	>
		<p class="font-semibold">Review sent. You can close this tab.</p>
	</div>
{:else}
	<TopBar {submitting} {error} onSubmit={handleSubmit} onOpenModal={() => (showModal = true)} />

	{#if showModal}
		<ReviewModal onSubmit={handleSubmit} onClose={() => (showModal = false)} />
	{/if}
{/if}
