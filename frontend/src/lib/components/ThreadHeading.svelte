<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import Tag from '$lib/ui/Tag.svelte';
	import { headingOf } from './anchor-headings';
	import NewReplyMark from './NewReplyMark.svelte';
	import { severityTone } from './severity-tone';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const AnchorHeading = $derived(headingOf(thread.anchor));
	const unread = $derived(review.threads.reading.isUnread(thread.id));
</script>

<!-- The rest of the head of the thread's first turn, after who said it and when: what the thread hangs on and
	what state it is in; whose it is and what can be done to it stand at the head's far end (ThreadHeadEnd) -->
<AnchorHeading anchor={thread.anchor} />
{#if thread.severity !== 'note'}
	<Tag tone={severityTone(thread)} testId="comment-severity">{thread.severity}</Tag>
{/if}
{#if thread.anchor.outdated}
	<Tag tone="quiet" testId="comment-outdated">outdated</Tag>
{/if}
{#if thread.resolved}
	<Tag tone="quiet" testId="comment-resolved">resolved</Tag>
{/if}
{#if unread}
	<NewReplyMark />
{/if}
