<script lang="ts">
	import type { Component } from 'svelte';
	import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
	import type { Review } from '$lib/review/review.svelte';
	import { provideReview } from '$lib/review/context';
	import { markTab } from '$lib/dom/tab';
	import Button from '$lib/ui/Button.svelte';
	import { COMMENTS, counted } from '$lib/utils/words';
	import AgentPanel from './AgentPanel.svelte';
	import { reportBroken } from './broken-parts';
	import DiffNotice from './DiffNotice.svelte';
	import DiffView from './DiffView.svelte';
	import FileList from './FileList.svelte';
	import Guide from './Guide.svelte';
	import { pressKey } from './keymap';
	import NoticeBar from './NoticeBar.svelte';
	import ReviewHeader from './ReviewHeader.svelte';
	import StoryContents from './StoryContents.svelte';
	import StoryNotice from './StoryNotice.svelte';
	import StoryView from './StoryView.svelte';
	import PartFailed from './PartFailed.svelte';

	interface Props {
		review: Review;
	}

	// What each way of reading the review draws: the reading itself, and what stands beside it as the
	// way through it. Another way of reading is another row here, never a longer chain in the markup
	const DRAWN_AS: Record<ReadingViewName, { beside: Component; reading: Component }> = {
		files: { beside: FileList, reading: DiffView },
		story: { beside: StoryContents, reading: StoryView }
	};

	let { review }: Props = $props();

	const drawn = $derived(DRAWN_AS[review.views.onScreen.name]);

	// Everything drawn below reads the review from here. The screen is drawn
	// for one review and never handed another, so its first is its only one.
	// svelte-ignore state_referenced_locally
	provideReview(review);

	// What has arrived from the agent and is not read yet: threads with an
	// answer or raised by it, and answers that landed in the panel while it was shut
	const arrived = $derived(review.threads.unread.length + review.layout.agentPanel.unread);

	// An answer can arrive while the review is in a background tab, where
	// neither the dot beside the thread nor the panel can be seen. The icon
	// is painted in the page's colours, so again once another theme is applied
	$effect(() => {
		void review.theme.applied;
		markTab(arrived, review.title);
	});
</script>

<!-- The review's keys, from anywhere on the page -->
<svelte:window onkeydown={(event: KeyboardEvent) => pressKey(review, event)} />

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
		<NoticeBar testId="restored-notice" kind="cr-notice-taken" icon="check">
			Picked up {counted(review.restoredCount, COMMENTS)} you had not sent yet.
			{#snippet actions()}
				<Button tone="quiet" size="xs" data-testid="dismiss-restored" onclick={() => review.dismissRestored()}>
					Dismiss
				</Button>
			{/snippet}
		</NoticeBar>
	{/if}
	{#if review.draftSetAside}
		<!-- With the other news about the review: why unsent work it may have
			left here is not on screen, and that it is kept rather than lost -->
		<NoticeBar testId="draft-set-aside" kind="cr-notice-set-aside" icon="notice">
			A kept draft could not be read; it is set aside.
			{#snippet actions()}
				<Button tone="quiet" size="xs" data-testid="dismiss-set-aside" onclick={() => review.dismissSetAside()}>
					Dismiss
				</Button>
			{/snippet}
		</NoticeBar>
	{/if}
	<DiffNotice />
	<!-- What a story says of itself, while it is the story that is read: a bar above the reading
		area, as the diff's own are, so it stands however far down the story the reader is -->
	{#if review.views.onScreen.name === 'story'}
		<StoryNotice />
	{/if}
	<div class="cr-columns">
		<!-- The review as it is read now, and the column that is the way through it: each stays drawn
			whether its column stands beside it or is put away to its rail -->
		<drawn.beside />
		<drawn.reading />
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
