<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { plainWords } from '$lib/utils/plain-words';
	import { AGENT } from '$lib/utils/speakers';
	import Popover from './Popover.svelte';

	// What the pane is called, and headed with
	const REPLIES = 'Replies';

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
		return plainWords(thread.turns.findLast((turn) => turn.author === AGENT)?.body ?? '');
	}

	function goTo(thread: Thread) {
		open = false;
		review.navigator.readAnswer(thread);
	}
</script>

<!-- How many are unread, and the way to read them all at once, beside the pane's heading -->
{#snippet unreadOfThem()}
	<span class="cr-muted text-xs">
		{review.threads.unread.length} unread
	</span>
	<!-- Nothing to do while everything has been read: offered, it would do nothing -->
	<Button
		tone="quiet"
		size="xs"
		testId="mark-all-read"
		disabled={review.threads.unread.length === 0}
		onclick={() => review.threads.reading.markAllRead()}
	>
		Mark all read
	</Button>
{/snippet}

<Popover
	bind:open
	label={REPLIES}
	heading={REPLIES}
	aside={unreadOfThem}
	placement="below-end"
	width="wide"
	testId="replies-list"
>
	{#snippet trigger(control)}
		<Button {...control} tone="quiet" size="xs" testId="replies-menu">
			<Icon name="reply" size="sm" />
			Replies
			{#if review.threads.unread.length > 0}
				<span data-testid="unread-count" class="text-(--cr-unread)">
					{review.threads.unread.length}
				</span>
			{/if}
		</Button>
	{/snippet}

	<!-- One row a thread, ruled off from the next -->
	<div class="divide-y divide-base-300">
		{#each threads as thread (thread.id)}
			{@const unread = review.threads.reading.isUnread(thread.id)}
			<button
				type="button"
				data-testid="reply-row"
				class="cr-pressable flex w-full gap-2 px-3 py-2 text-left"
				onclick={() => goTo(thread)}
			>
				<span class="w-2 pt-1.5">
					{#if unread}
						<span class="block h-1.5 w-1.5 rounded-full bg-(--cr-unread)"></span>
						<span class="sr-only">unread:</span>
					{/if}
				</span>
				<span class="min-w-0 flex-1">
					<span class={['block font-mono text-xs', unread ? 'text-(--cr-unread)' : 'cr-muted']}>
						{anchorShortPlace(thread.anchor)}
					</span>
					<span class="cr-muted block truncate text-sm">{lastAnswer(thread)}</span>
				</span>
			</button>
		{:else}
			<p data-testid="no-replies" class="cr-muted px-3 py-6 text-center text-xs">Nothing new. Answers land here.</p>
		{/each}
	</div>
</Popover>
