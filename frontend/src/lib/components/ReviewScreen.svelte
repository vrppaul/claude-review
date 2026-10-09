<script lang="ts">
	import type { Review } from '$lib/review/review.svelte';
	import { provideReview } from '$lib/review/context';
	import { markTab } from '$lib/utils/tab';
	import AgentPanel from './AgentPanel.svelte';
	import DiffNotice from './DiffNotice.svelte';
	import DiffView from './DiffView.svelte';
	import FileList from './FileList.svelte';
	import Guide from './Guide.svelte';
	import KeyboardShortcuts from './KeyboardShortcuts.svelte';
	import SubmitBar from './SubmitBar.svelte';

	interface Props {
		review: Review;
	}

	let { review }: Props = $props();

	// Everything drawn below reads the review from here. The screen is drawn
	// for one review and never handed another, so its first is its only one.
	// svelte-ignore state_referenced_locally
	provideReview(review);

	// An answer can arrive while the review is in a background tab, where
	// neither the dot beside the thread nor the panel can be seen
	$effect(() => {
		markTab(review.threads.unread.length + review.layout.agentPanel.unread, review.title);
	});
</script>

{#if review.diff.files.length === 0 && !review.diff.narrowed}
	<div class="flex items-center justify-center min-h-screen">
		<div class="alert alert-info max-w-md">
			<span>No changes found.</span>
		</div>
	</div>
{:else}
	<KeyboardShortcuts />
	<Guide />
	<div class="flex h-screen flex-col">
		{#if review.restoredCount > 0}
			<div
				data-testid="restored-notice"
				class="flex items-center gap-3 border-b border-base-300 bg-base-200 px-4 py-1.5 text-xs"
			>
				<span>
					Picked up {review.restoredCount}
					{review.restoredCount === 1 ? 'comment' : 'comments'} you had not sent yet.
				</span>
				<button class="btn btn-ghost btn-xs" onclick={() => review.dismissRestored()}>Dismiss</button>
			</div>
		{/if}
		<SubmitBar />
		<DiffNotice />
		<div class="flex min-h-0 flex-1">
			{#if review.layout.fileTree.open}
				<FileList />
			{:else}
				<!-- Where the tree was, so the way back is where it went -->
				<button
					data-testid="show-sidebar"
					data-tour="file-tree"
					class="cr-tree-rail"
					title="Bring the file tree back"
					aria-label="Bring the file tree back"
					onclick={() => review.layout.fileTree.toggle()}
				>
					<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
						<path d="M4.5 2L8 6l-3.5 4z" />
					</svg>
				</button>
			{/if}
			<DiffView />
			{#if review.layout.agentPanel.open}
				<AgentPanel />
			{/if}
		</div>
	</div>
{/if}
