<script lang="ts">
	import type { Thread } from '$lib/types';
	import { blockKey } from '$lib/anchors/story';
	import { threadPlaceOf } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { OVERVIEW_PART } from '$lib/review/story-keys';
	import { placeKey } from '$lib/utils/line-places';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { headingOf } from './anchor-headings';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import FoldToggle from './FoldToggle.svelte';
	import NewReplyMark from './NewReplyMark.svelte';
	import ReopenButton from './ReopenButton.svelte';

	// What is asked before a thread is deleted, and its two answers
	const DELETE_QUESTION = 'Delete this comment?';
	const DELETE = 'Delete';
	const KEEP_IT = 'Keep it';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const AnchorHeading = $derived(headingOf(thread.anchor));
	const unread = $derived(review.threads.reading.isUnread(thread.id));
	// Which round it went out in, if it has
	const sentIn = $derived(review.threads.sentInRound(thread.id));
	// A thread the agent raised is the agent's: the reader answers its words and
	// settles it, and never rewrites it nor deletes it — the review keeps it
	// whatever a page says, and it would come back
	const raised = $derived(raisedByAgent(thread));
	// Whether the reader is being asked if the thread, and all said in it, may go
	let askingToDelete = $state(false);

	/** Fold the thread away; the keyboard stays on the toggle, drawn anew on the folded line. */
	function foldAway() {
		review.threads.reading.setFolded(thread.id, true);
		review.sections.keyboardToThreadFold(thread.id);
	}

	/** Settle the thread, which folds it; the keyboard stays with it. */
	function resolve() {
		review.threads.setResolved(thread.id, true);
		review.sections.keyboardToThread(thread.id);
	}

	/**
	 * Delete the thread; the keyboard goes back to the line it hung under, or
	 * to what offered the block it hung on, or, for a block the story no
	 * longer draws, to the head of the story the thread stood at.
	 */
	function remove() {
		const place = threadPlaceOf(thread.anchor);
		review.threads.remove(thread.id);
		switch (place.on) {
			case 'lines': {
				const { lines } = place;
				review.sections.keyboardToLine(lines.file, placeKey({ side: lines.side, number: lines.end_line }));
				break;
			}
			case 'story':
				// Each gives the keyboard only where it is still on nothing, in the order asked: the block first
				review.sections.keyboardToBlock(blockKey(place.block));
				review.parts.keyboardToHeadOf(OVERVIEW_PART);
				break;
		}
	}
</script>

<!-- What the thread hangs on and what state it is in, and what can be done to it -->
<div class="flex items-center gap-2">
	<FoldToggle folded={false} subject="this thread" testId="fold-comment" onToggle={foldAway} />
	<AnchorHeading anchor={thread.anchor} />
	{#if thread.severity !== 'note'}
		<span data-testid="comment-severity" class="cr-tag cr-severity-{thread.severity}">{thread.severity}</span>
	{/if}
	{#if thread.anchor.outdated}
		<span data-testid="comment-outdated" class="cr-tag cr-muted">outdated</span>
	{/if}
	{#if thread.resolved}
		<span data-testid="comment-resolved" class="cr-tag cr-muted">resolved</span>
	{/if}
	{#if unread}
		<NewReplyMark />
	{/if}
	<div class="flex-1"></div>
	{#if raised}
		<span data-testid="comment-raised" class="cr-tag cr-raised-tag">from the agent</span>
	{:else if sentIn !== undefined}
		<span data-testid="comment-sent" class="cr-faint text-xs">sent · round {sentIn}</span>
	{/if}
	<div class="flex gap-1 opacity-45 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
		{#if !raised}
			<button
				type="button"
				data-testid="edit-comment"
				class="btn btn-ghost btn-xs"
				onclick={() => review.threads.writing.openEdit(thread)}
			>
				Edit
			</button>
		{/if}
		{#if thread.resolved}
			<ReopenButton {thread} />
		{:else}
			<!-- Settling a thread folds it away; it can still be opened and read -->
			<button type="button" data-testid="resolve-comment" class="btn btn-ghost btn-xs" onclick={resolve}>
				Resolve
			</button>
		{/if}
		{#if !raised}
			<button
				type="button"
				data-testid="delete-comment"
				class="btn btn-ghost btn-xs hover:text-error"
				onclick={() => (askingToDelete = true)}
			>
				Delete
			</button>
		{/if}
	</div>
</div>
{#if askingToDelete}
	<ConfirmDialog
		question={DELETE_QUESTION}
		goAhead={DELETE}
		keep={KEEP_IT}
		testId="delete-dialog"
		onGoAhead={remove}
		onClose={() => (askingToDelete = false)}
	/>
{/if}
