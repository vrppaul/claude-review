<script lang="ts">
	import { onMount } from 'svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { openSession } from '$lib/stores/session.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { soundStore } from '$lib/stores/sound.svelte';
	import { markTab } from '$lib/utils/tab';
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

		// Holding this open is what tells the server the review is still on
		// screen; a poll is throttled to a crawl in a background tab.
		return openSession(handle);
	});

	/** What the server has to say while the review is open. */
	function handle(message: { type: string; [key: string]: unknown }) {
		if (message.type === 'reply' && typeof message.text === 'string') {
			commentStore.receiveReply(
				String(message.thread_id),
				message.text,
				typeof message.question_id === 'string' ? message.question_id : undefined
			);
			soundStore.announce();
		} else if (message.type === 'answerer') {
			reviewStore.attachAnswerer();
		} else if (message.type === 'round' && typeof message.number === 'number') {
			reviewStore.setRound(message.number);
		} else if (message.type === 'diff') {
			// The work a round asked for has landed. Take the diff again and
			// move the threads onto it: one whose lines survived follows them,
			// one whose lines are gone says so.
			void diffStore.fetchDiff().then(() => commentStore.reanchorAll(diffStore.files));
		}
	}

	// An answer can arrive while the review is in a background tab, where the
	// dot beside the thread cannot be seen
	$effect(() => {
		markTab(commentStore.unreadCount, diffStore.title || 'Claude Review');
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
	<div class="flex h-screen flex-col">
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
		<SubmitBar />
		<div class="flex min-h-0 flex-1">
			<FileList />
			<DiffView />
		</div>
	</div>
{/if}
