<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { AGENT } from '$lib/utils/speakers';
	import Icon from './Icon.svelte';
	import Popover from './Popover.svelte';

	const review = useReview();

	let open = $state(false);

	// Unread first: what changed since the reader last looked is the reason
	// this list exists at all
	const threads = $derived([
		...review.threads.unread,
		...review.threads.answered.filter((thread) => !review.threads.reading.isUnread(thread.id))
	]);

	/** What the agent last said in a thread. */
	function lastAnswer(thread: Thread): string {
		return thread.turns.findLast((turn) => turn.author === AGENT)?.body ?? '';
	}

	function goTo(thread: Thread) {
		open = false;
		review.navigator.reveal(thread);
		review.threads.reading.markRead(thread.id);
	}
</script>

<Popover bind:open label="Replies" placement="below-end" data-testid="replies-list" class="w-96">
	{#snippet trigger(control)}
		<button {...control} type="button" data-testid="replies-menu" class="cr-chip">
			<Icon name="reply" class="h-3.5 w-3.5" />
			Replies
			{#if review.threads.unread.length > 0}
				<span data-testid="unread-count" class="font-semibold text-(--cr-mark)">
					{review.threads.unread.length}
				</span>
			{/if}
		</button>
	{/snippet}

	<div class="flex items-center gap-2 px-3 py-2">
		<span class="text-xs font-semibold">Replies</span>
		<span class="cr-muted text-xs">
			{review.threads.unread.length} unread
		</span>
		<div class="flex-1"></div>
		<button
			type="button"
			data-testid="mark-all-read"
			class="btn btn-ghost btn-xs"
			onclick={() => review.threads.reading.markAllRead()}
		>
			Mark all read
		</button>
	</div>

	{#each threads as thread (thread.id)}
		{@const unread = review.threads.reading.isUnread(thread.id)}
		<button
			type="button"
			data-testid="reply-row"
			class="flex w-full gap-2 border-t border-base-300 px-3 py-2 text-left hover:bg-base-300"
			onclick={() => goTo(thread)}
		>
			<span class="w-2 pt-1.5">
				{#if unread}
					<span class="block h-1.5 w-1.5 rounded-full bg-(--cr-mark)"></span>
				{/if}
			</span>
			<span class="min-w-0 flex-1">
				<span class={['block font-mono text-xs', unread ? 'text-(--cr-mark)' : 'cr-muted']}>
					{anchorShortPlace(thread.anchor)}
				</span>
				<span class="cr-muted block truncate text-sm">{lastAnswer(thread)}</span>
			</span>
		</button>
	{:else}
		<p data-testid="no-replies" class="cr-muted border-t border-base-300 px-3 py-6 text-center text-xs">
			Nothing new. Answers land here.
		</p>
	{/each}
</Popover>
