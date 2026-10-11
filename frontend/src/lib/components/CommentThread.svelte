<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorLabel } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import CommentBox from './CommentBox.svelte';
	import FoldedThread from './FoldedThread.svelte';
	import OpenThread from './OpenThread.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	let container: HTMLElement | undefined = $state();

	// Announced to the review, which brings the thread into view by it, never by an id on the page
	$effect(() => (container ? review.sections.registerThread(thread.id, container) : undefined));

	// The opening comment being rewritten, held by the review so that folding
	// the thread or its file, or reloading the page, keeps it
	const editing = $derived(review.threads.writing.edit(thread.id));
</script>

<!-- A thread, drawn the way it is being read: rewritten, folded away, or open. The
	keyboard is put on it when the reader is taken to it, whichever way it is drawn -->
<div bind:this={container} data-testid="comment-thread" data-thread-id={thread.id} class="px-3 py-2" tabindex="-1">
	{#if editing}
		<CommentBox
			field={editing}
			onSave={() => review.threads.say(editing)}
			onCancel={() => review.threads.writing.discard(editing)}
			label={anchorLabel(thread.anchor)}
		/>
	{:else if review.threads.reading.isFolded(thread.id)}
		<FoldedThread {thread} />
	{:else}
		<OpenThread {thread} />
	{/if}
</div>
