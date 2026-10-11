<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { headingOf } from './anchor-headings';
	import FoldToggle from './FoldToggle.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const AnchorHeading = $derived(headingOf(thread.anchor));
	const unread = $derived(review.threads.reading.isUnread(thread.id));
	// Which round it went out in, if it has
	const sentIn = $derived(review.threads.sentInRound(thread.id));
</script>

<!-- What the thread hangs on and what state it is in, and what can be done to it -->
<div class="mb-2 flex items-center gap-2">
	<FoldToggle
		folded={false}
		foldLabel="Fold this thread away"
		unfoldLabel="Unfold this thread"
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
		<span data-testid="comment-unread" class="text-xs text-(--cr-mark)"
			><span aria-hidden="true">●</span> new reply</span
		>
	{/if}
	<div class="flex-1"></div>
	{#if raisedByAgent(thread)}
		<span data-testid="comment-raised" class="cr-severity cr-raised-tag">from the agent</span>
	{:else if sentIn !== undefined}
		<span data-testid="comment-sent" class="cr-faint text-xs">sent · round {sentIn}</span>
	{/if}
	<div class="flex gap-1 opacity-45 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
		<button
			type="button"
			data-testid="edit-comment"
			class="btn btn-ghost btn-xs"
			onclick={() => review.threads.writing.openEdit(thread)}
		>
			Edit
		</button>
		{#if thread.resolved}
			<button
				type="button"
				data-testid="reopen-comment"
				class="btn btn-ghost btn-xs"
				onclick={() => review.threads.setResolved(thread.id, false)}
			>
				Reopen
			</button>
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
		<button
			type="button"
			data-testid="delete-comment"
			class="btn btn-ghost btn-xs hover:text-error"
			onclick={() => review.threads.remove(thread.id)}
		>
			Delete
		</button>
	</div>
</div>
