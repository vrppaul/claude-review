<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Count from '$lib/ui/Count.svelte';
	import Dot from '$lib/ui/Dot.svelte';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { plainWords } from '$lib/utils/plain-words';
	import { AGENT } from '$lib/utils/speakers';

	// What the pane is called, and headed with
	const REPLIES = 'Replies';

	const review = useReview();

	let open = $state(false);

	// How many answers wait unread: on the mark's corner, and in its name for whoever cannot see the figure
	const unread = $derived(review.threads.unread.length);
	const repliesNamed = $derived(unread > 0 ? `${REPLIES}, ${unread} unread` : REPLIES);

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
		{unread} unread
	</span>
	<!-- Nothing to do while everything has been read: offered, it would do nothing -->
	<Button
		tone="quiet"
		size="xs"
		testId="mark-all-read"
		disabled={unread === 0}
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
		<IconButton {...control} tone="quiet" size="xs" label={repliesNamed} testId="replies-menu">
			<Icon name="reply" size="sm" />
			{#snippet corner()}
				{#if unread > 0}
					<Count tone="unread" count={unread} aria-hidden testId="unread-count" />
				{/if}
			{/snippet}
		</IconButton>
	{/snippet}

	<!-- One row a thread, inside the pane's margin: where it hangs, and what the agent last said in it -->
	<div class="p-1">
		{#each threads as thread (thread.id)}
			{@const unread = review.threads.reading.isUnread(thread.id)}
			<Row names="path" testId="reply-row" onclick={() => goTo(thread)}>
				{#snippet leading()}
					<!-- Room for the mark of an unread answer in every row, so where each hangs stands in one line -->
					<span class="flex w-(--cr-list-row-dot-slot)">
						{#if unread}
							<Dot tone="unread" testId="reply-unread" />
							<span class="sr-only">unread:</span>
						{/if}
					</span>
				{/snippet}
				{#snippet label()}
					<span class={unread ? 'text-(--cr-unread)' : 'cr-muted'}>{anchorShortPlace(thread.anchor)}</span>
				{/snippet}
				{#snippet said()}
					{lastAnswer(thread)}
				{/snippet}
			</Row>
		{:else}
			<EmptyNote within="list" testId="no-replies">Nothing new. Answers land here.</EmptyNote>
		{/each}
	</div>
</Popover>
