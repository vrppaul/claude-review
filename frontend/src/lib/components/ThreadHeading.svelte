<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';
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
</script>

<!-- What the thread hangs on and what state it is in, and what can be done to it -->
<div class="mb-2 flex items-center gap-2">
	<FoldToggle
		folded={false}
		subject="this thread"
		testId="fold-comment"
		onToggle={() => review.threads.reading.setFolded(thread.id, true)}
	/>
	<AnchorHeading anchor={thread.anchor} />
	{#if thread.severity !== 'note'}
		<span data-testid="comment-severity" class="cr-severity cr-severity-{thread.severity}">{thread.severity}</span>
	{/if}
	{#if thread.anchor.outdated}
		<span data-testid="comment-outdated" class="cr-severity cr-muted">outdated</span>
	{/if}
	{#if thread.resolved}
		<span data-testid="comment-resolved" class="cr-severity cr-muted">resolved</span>
	{/if}
	{#if unread}
		<NewReplyMark />
	{/if}
	<div class="flex-1"></div>
	{#if raised}
		<span data-testid="comment-raised" class="cr-severity cr-raised-tag">from the agent</span>
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
			<button
				type="button"
				data-testid="resolve-comment"
				class="btn btn-ghost btn-xs"
				onclick={() => review.threads.setResolved(thread.id, true)}
			>
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
		onGoAhead={() => review.threads.remove(thread.id)}
		onClose={() => (askingToDelete = false)}
	/>
{/if}
