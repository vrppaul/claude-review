<script lang="ts">
	import type { Review } from '$lib/review/review.svelte';
	import { provideReview } from '$lib/review/context';
	import { markTab } from '$lib/dom/tab';
	import { counted } from '$lib/utils/words';
	import AgentPanel from './AgentPanel.svelte';
	import { reportBroken } from './broken-parts';
	import DiffNotice from './DiffNotice.svelte';
	import DiffView from './DiffView.svelte';
	import FileList from './FileList.svelte';
	import Guide from './Guide.svelte';
	import HelpDialog from './HelpDialog.svelte';
	import { pressKey } from './keymap';
	import ReviewHeader from './ReviewHeader.svelte';
	import Icon from './Icon.svelte';
	import PartFailed from './PartFailed.svelte';

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

<!-- The review's keys, from anywhere on the page -->
<svelte:window onkeydown={(event: KeyboardEvent) => pressKey(review, event)} />

{#if review.guide.helpOpen}
	<HelpDialog />
{/if}
<Guide />
<div class="flex h-screen flex-col">
	{#if review.restoredCount > 0}
		<div
			data-testid="restored-notice"
			class="flex items-center gap-3 border-b border-base-300 bg-base-200 px-4 py-1.5 text-xs"
		>
			<span>
				Picked up {counted(review.restoredCount, 'comment', 'comments')} you had not sent yet.
			</span>
			<button
				type="button"
				data-testid="dismiss-restored"
				class="btn btn-ghost btn-xs"
				onclick={() => review.dismissRestored()}
			>
				Dismiss
			</button>
		</div>
	{/if}
	<ReviewHeader />
	<DiffNotice />
	<div class="flex min-h-0 flex-1">
		{#if review.layout.fileTree.open}
			<FileList />
		{:else}
			<!-- Where the tree was, so the way back is where it went -->
			<button
				type="button"
				data-testid="show-sidebar"
				data-tour="file-tree"
				class="cr-tree-rail"
				title="Bring the file tree back"
				aria-label="Bring the file tree back"
				onclick={() => review.layout.fileTree.toggle()}
			>
				<Icon name="caret" class="h-3 w-3" />
			</button>
		{/if}
		<DiffView />
		{#if review.layout.agentPanel.open}
			<!-- A panel that cannot be drawn says so in its column, and leaves the review to be read and sent -->
			<svelte:boundary onerror={reportBroken}>
				<AgentPanel />
				{#snippet failed(error, retry)}
					<!-- Where the panel stood, as wide, so the review beside it does not move -->
					<div
						class="cr-panel shrink-0 border-l border-base-300"
						style:--cr-panel-width="{review.layout.agentPanel.width}px"
					>
						<PartFailed what="The agent panel" {error} {retry} />
					</div>
				{/snippet}
			</svelte:boundary>
		{/if}
	</div>
</div>
