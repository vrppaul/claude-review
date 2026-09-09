<script lang="ts">
	import type { Comment } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { soundStore } from '$lib/stores/sound.svelte';
	import { lineRangeLabel } from '$lib/utils/line-label';
	import { scrollToComment } from '$lib/utils/scroll';

	let open = $state(false);
	let container = $state<HTMLElement>();

	// Unread first: what changed since the reader last looked is the reason
	// this list exists at all
	const threads = $derived([
		...commentStore.unread,
		...commentStore.answered.filter((c) => !c.unread)
	]);

	function lastAnswer(comment: Comment): string {
		return [...comment.turns].reverse().find((t) => t.author === 'author')?.body ?? '';
	}

	function goTo(comment: Comment) {
		open = false;
		if (diffStore.isCollapsed(comment.file)) diffStore.toggleCollapsed(comment.file);
		requestAnimationFrame(() => {
			scrollToComment(comment.id, comment.file);
			commentStore.markRead(comment.id);
		});
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
	<button
		data-testid="replies-menu"
		class="cr-chip"
		aria-expanded={open}
		onclick={() => (open = !open)}
	>
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
		{#if commentStore.unreadCount > 0}
			<span data-testid="unread-count" class="font-semibold" style="color: var(--cr-mark)">
				{commentStore.unreadCount}
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
					{commentStore.unreadCount} unread
				</span>
				<div class="flex-1"></div>
				<button class="btn btn-ghost btn-xs" onclick={() => commentStore.markAllRead()}>
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
						{#if comment.unread}
							<span class="block h-1.5 w-1.5 rounded-full" style="background: var(--cr-mark)"></span>
						{/if}
					</span>
					<span class="min-w-0 flex-1">
						<span class="flex items-baseline gap-2">
							<span class="font-mono text-xs {comment.unread ? '' : 'cr-muted'}"
								style={comment.unread ? 'color: var(--cr-mark)' : ''}
							>
								{comment.file.split('/').pop()}
								{lineRangeLabel(comment.side, comment.start_line, comment.end_line)}
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

			<div class="flex items-center border-t border-base-300 px-3 py-2">
				<label class="cr-chip">
					<input
						data-testid="reply-sound"
						type="checkbox"
						checked={soundStore.enabled}
						onchange={() => soundStore.toggle()}
					/>
					<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
						{#if soundStore.enabled}
							<path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" />
						{:else}
							<circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1" />
						{/if}
					</svg>
					Tick on a new reply
				</label>
				<div class="flex-1"></div>
				<span class="cr-faint text-xs">only in a background tab</span>
			</div>
		</div>
	{/if}
</div>
