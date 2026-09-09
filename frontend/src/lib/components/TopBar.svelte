<script lang="ts">
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { reviewStore } from '$lib/stores/review.svelte';
	import { scrollToComment } from '$lib/utils/scroll';
	import DiffLayoutToggle from './DiffLayoutToggle.svelte';
	import RepliesMenu from './RepliesMenu.svelte';
	import ThemeToggle from './ThemeToggle.svelte';

	interface Props {
		submitting: boolean;
		error: string | null;
		onSubmit: () => void;
		onSendRound: () => void;
		onEnd: () => void;
		onOpenModal: () => void;
	}

	let { submitting, error, onSubmit, onSendRound, onEnd, onOpenModal }: Props = $props();

	// A round is only worth offering while something is there to work through
	// it; on its own, sending is the end of the review
	const inRounds = $derived(reviewStore.canSendRound);

	function step(direction: 1 | -1) {
		const comment = commentStore.step(direction);
		if (!comment) return;

		// A folded file has no comment on screen to move to, so open it first
		if (diffStore.isCollapsed(comment.file)) {
			diffStore.toggleCollapsed(comment.file);
		}
		requestAnimationFrame(() => scrollToComment(comment.id, comment.file));
	}
</script>

<header
	data-testid="top-bar"
	class="flex h-12 shrink-0 items-center gap-3 border-b border-base-300 bg-base-200 px-4"
>
	<span class="font-semibold">Review</span>
	<span class="cr-muted hidden text-xs lg:inline">? for keys</span>
	{#if diffStore.title}
		<span data-testid="review-title" class="cr-muted truncate font-mono text-xs">
			{diffStore.title}
		</span>
	{/if}

	<div class="flex-1"></div>

	{#if diffStore.mode === 'diff'}
		<label class="cr-chip">
			<input
				data-testid="ignore-whitespace"
				type="checkbox"
				checked={diffStore.ignoreWhitespace}
				onchange={(e) => diffStore.setIgnoreWhitespace(e.currentTarget.checked)}
			/>
			<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
				{#if diffStore.ignoreWhitespace}
					<path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" />
				{:else}
					<circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1" />
				{/if}
			</svg>
			Ignore whitespace
		</label>
		<DiffLayoutToggle />
	{/if}

	{#if error}
		<span data-testid="submit-error" class="text-sm text-error">{error}</span>
	{/if}

	{#if commentStore.answered.length > 0}
		<RepliesMenu />
	{/if}

	<span data-testid="comment-count" class="cr-muted text-sm">
		{#if inRounds}
			{commentStore.unsentCount} unsent · {commentStore.count}
		{:else}
			{commentStore.count}
			{commentStore.count === 1 ? 'comment' : 'comments'}
		{/if}
	</span>

	{#if commentStore.count > 0}
		<div class="join">
			<button
				data-testid="prev-comment"
				class="btn join-item btn-ghost btn-xs"
				onclick={() => step(-1)}
				title="Previous comment"
				aria-label="Previous comment"
			>
				<svg class="h-3 w-3 rotate-180" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
					<path d="M2 4l4 4 4-4z" />
				</svg>
			</button>
			<button
				data-testid="next-comment"
				class="btn join-item btn-ghost btn-xs"
				onclick={() => step(1)}
				title="Next comment"
				aria-label="Next comment"
			>
				<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
					<path d="M2 4l4 4 4-4z" />
				</svg>
			</button>
		</div>
	{/if}

	<button class="btn btn-ghost btn-sm" data-testid="finish-review" onclick={onOpenModal}>
		Add a summary
	</button>
	{#if inRounds}
		<button class="btn btn-outline btn-sm" data-testid="end-review" onclick={onEnd}>
			End review
		</button>
	{/if}
	<button
		class="btn btn-primary btn-sm"
		data-testid="quick-submit"
		disabled={!commentStore.hasUnsent || submitting}
		onclick={inRounds ? onSendRound : onSubmit}
		title="Ctrl+Shift+Enter"
	>
		{#if submitting}
			<span class="loading loading-xs loading-spinner"></span>
			Sending
		{:else if inRounds}
			Send round {reviewStore.round}
		{:else}
			Send review
		{/if}
	</button>

	<ThemeToggle />
</header>
