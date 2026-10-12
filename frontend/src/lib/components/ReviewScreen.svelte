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

	// What has arrived from the agent and is not read yet: threads with an
	// answer or raised by it, and answers that landed in the panel while it was shut
	const arrived = $derived(review.threads.unread.length + review.layout.agentPanel.unread);

	// An answer can arrive while the review is in a background tab, where
	// neither the dot beside the thread nor the panel can be seen
	$effect(() => {
		markTab(arrived, review.title);
	});
</script>

<!-- The review's keys, from anywhere on the page -->
<svelte:window onkeydown={(event: KeyboardEvent) => pressKey(review, event)} />

{#if review.guide.helpOpen}
	<HelpDialog />
{/if}
<Guide />
<!-- The dots are for the eye; this says the same aloud as it changes, without moving the keyboard -->
<p data-testid="arrivals" role="status" class="sr-only">
	{arrived > 0 ? `${arrived} new from the agent, not read yet` : ''}
</p>
<div class="flex h-screen flex-col">
	<ReviewHeader />
	{#if review.restoredCount > 0}
		<!-- Under the header, with the other news about the review: what the
			draft brought back, counted as the header counts what is unsent -->
		<div
			data-testid="restored-notice"
			class="cr-notice cr-notice-taken flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
		>
			<Icon name="check" class="h-3 w-3 shrink-0" />
			<span>
				Picked up {counted(review.restoredCount, 'comment', 'comments')} you had not sent yet.
			</span>
			<div class="flex-1"></div>
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
	{#if review.draftSetAside}
		<!-- With the other news about the review: why unsent work it may have
			left here is not on screen, and that it is kept rather than lost -->
		<div
			data-testid="draft-set-aside"
			class="cr-notice cr-notice-set-aside flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
		>
			<Icon name="notice" class="h-3 w-3 shrink-0" />
			<span>A kept draft could not be read; it is set aside.</span>
			<div class="flex-1"></div>
			<button
				type="button"
				data-testid="dismiss-set-aside"
				class="btn btn-ghost btn-xs"
				onclick={() => review.dismissSetAside()}
			>
				Dismiss
			</button>
		</div>
	{/if}
	<DiffNotice />
	<div class="cr-columns">
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
					<div class="cr-panel border-l border-base-300" style:--cr-panel-width="{review.layout.agentPanel.width}px">
						<PartFailed what="The agent panel" {error} {retry} />
					</div>
				{/snippet}
			</svelte:boundary>
		{/if}
	</div>
</div>
