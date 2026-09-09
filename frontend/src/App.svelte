<script lang="ts">
	import { onMount } from 'svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import FileList from '$lib/components/FileList.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import SubmitBar from '$lib/components/SubmitBar.svelte';
	import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let restored = $state(0);

	onMount(() => {
		diffStore
			.fetchDiff()
			.then(() => {
				// An unsent review of the same thing is picked up where it stopped
				restored = commentStore.restore(diffStore.title);
			})
			.catch((e) => {
				error = e instanceof Error ? e.message : 'Failed to load diff';
			})
			.finally(() => {
				loading = false;
			});

		// Heartbeat so server knows browser is still open
		const interval = setInterval(() => {
			fetch('/api/heartbeat', { method: 'POST' }).catch(() => {});
		}, 3000);
		return () => clearInterval(interval);
	});
</script>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<span class="loading loading-spinner loading-lg"></span>
	</div>
{:else if error}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-error max-w-md">
			<span>{error}</span>
		</div>
	</div>
{:else if diffStore.files.length === 0}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-info max-w-md">
			<span>No changes found.</span>
		</div>
	</div>
{:else}
	<KeyboardShortcuts />
	{#if restored > 0}
		<div
			data-testid="restored-notice"
			class="flex items-center gap-3 border-b border-base-300 bg-base-200 px-4 py-1.5 text-xs"
		>
			<span>
				Picked up {restored}
				{restored === 1 ? 'comment' : 'comments'} you had not sent yet.
			</span>
			<button class="btn btn-ghost btn-xs" onclick={() => (restored = 0)}>Dismiss</button>
		</div>
	{/if}
	<div class="flex h-screen flex-col">
		<SubmitBar />
		<div class="flex min-h-0 flex-1">
			<FileList />
			<DiffView />
		</div>
	</div>
{/if}
