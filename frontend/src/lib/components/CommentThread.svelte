<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorLabel, anchorPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import type { CardHanging } from '$lib/ui/card';
	import CommentBox from './CommentBox.svelte';
	import ThreadCard from './ThreadCard.svelte';

	interface Props {
		thread: Thread;
		/** Where it hangs, open or being rewritten: under its line, under a block of the story's words, or at the head of what it lost its place in. */
		hangs: CardHanging;
	}

	let { thread, hangs }: Props = $props();
	const review = useReview();

	let container: HTMLElement | undefined = $state();

	// Announced to the review, which brings the thread into view by it, never by an id on the page
	$effect(() => (container ? review.sections.registerThread(thread.id, container) : undefined));

	// The opening comment being rewritten, held by the review so that folding
	// the thread or its file, or reloading the page, keeps it
	const editing = $derived(review.threads.writing.edit(thread.id));

	/** The edit is over, its words said or put away; the keyboard stays with the thread. */
	function editDone(done: () => void) {
		done();
		review.sections.keyboardToThread(thread.id);
	}
</script>

<!-- A thread, drawn the way it is being read: rewritten, folded away, or open. The
	keyboard is put on it when the reader is taken to it, whichever way it is drawn -->
<div
	bind:this={container}
	data-testid="comment-thread"
	data-thread-id={thread.id}
	class="cr-thread-hang"
	tabindex="-1"
	role="group"
	aria-label="Thread on {anchorPlace(thread.anchor)}"
>
	{#if editing}
		<CommentBox
			field={editing}
			onSave={() => editDone(() => review.threads.say(editing))}
			onCancel={() => editDone(() => review.threads.writing.discard(editing))}
			label={anchorLabel(thread.anchor)}
			{hangs}
		/>
	{:else}
		<ThreadCard {thread} {hangs} folded={review.threads.reading.isFolded(thread.id)} />
	{/if}
</div>
