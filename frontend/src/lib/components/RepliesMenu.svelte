<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';

	const review = useReview();

	let open = $state(false);
	let container = $state<HTMLElement>();

	// Unread first: what changed since the reader last looked is the reason
	// this list exists at all
	const threads = $derived([
		...review.threads.unread,
		...review.threads.answered.filter((thread) => !review.threads.reading.isUnread(thread.id))
	]);

	function lastAnswer(comment: Thread): string {
		return [...comment.turns].reverse().find((t) => t.author === 'author')?.body ?? '';
	}

	function goTo(comment: Thread) {
		open = false;
		review.navigator.reveal(comment);
		review.threads.reading.markRead(comment.id);
	}

	function onWindowClick(event: MouseEvent) {
		if (!open || !container) return;
		if (!container.contains(event.target as Node)) open = false;
	}
</script>

<svelte:window
	onclick={onWindowClick}
	onkeydown={(e) => {
		if (e.key === 'Escape') open = false;
	}}
/>

<div class="relative" bind:this={container}>
	<button data-testid="replies-menu" class="cr-chip" aria-expanded={open} onclick={() => (open = !open)}>
		<svg
			class="h-3.5 w-3.5"
			viewBox="0 0 16 16"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M4 3v5.5a2 2 0 0 0 2 2h6" />
			<path d="M9.5 8l3 2.5-3 2.5" />
		</svg>
		Replies
		{#if review.threads.unread.length > 0}
			<span data-testid="unread-count" class="font-semibold" style="color: var(--cr-mark)">
				{review.threads.unread.length}
			</span>
		{/if}
	</button>

	{#if open}
		<div
			data-testid="replies-list"
			class="cr-dialog absolute right-0 z-30 mt-2 w-96 overflow-hidden rounded-box bg-base-200"
		>
			<div class="flex items-center gap-2 px-3 py-2">
				<span class="text-xs font-semibold">Replies</span>
				<span class="cr-muted text-xs">
					{review.threads.unread.length} unread
				</span>
				<div class="flex-1"></div>
				<button class="btn btn-ghost btn-xs" onclick={() => review.threads.reading.markAllRead()}>
					Mark all read
				</button>
			</div>

			{#each threads as comment (comment.id)}
				<button
					data-testid="reply-row"
					class="flex w-full gap-2 border-t border-base-300 px-3 py-2 text-left hover:bg-base-300"
					onclick={() => goTo(comment)}
				>
					<span class="w-2 pt-1.5">
						{#if review.threads.reading.isUnread(comment.id)}
							<span class="block h-1.5 w-1.5 rounded-full" style="background: var(--cr-mark)"></span>
						{/if}
					</span>
					<span class="min-w-0 flex-1">
						<span class="flex items-baseline gap-2">
							<span
								class="font-mono text-xs {review.threads.reading.isUnread(comment.id) ? '' : 'cr-muted'}"
								style={review.threads.reading.isUnread(comment.id) ? 'color: var(--cr-mark)' : ''}
							>
								{anchorShortPlace(comment.anchor)}
							</span>
						</span>
						<span class="cr-muted block truncate text-sm">{lastAnswer(comment)}</span>
					</span>
				</button>
			{:else}
				<p data-testid="no-replies" class="cr-muted border-t border-base-300 px-3 py-6 text-center text-xs">
					Nothing new. Answers land here.
				</p>
			{/each}
		</div>
	{/if}
</div>
