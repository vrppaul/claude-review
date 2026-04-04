<script lang="ts">
	import { onMount } from 'svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import FileList from '$lib/components/FileList.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import SubmitBar from '$lib/components/SubmitBar.svelte';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(() => {
		diffStore
			.fetchDiff()
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
	<ThemeToggle />
	<div class="flex h-screen pb-14">
		<FileList />
		{#if diffStore.selectedFile}
			<DiffView file={diffStore.selectedFile} />
		{/if}
	</div>
	<SubmitBar />
{/if}
