<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import type { CardHanging } from '$lib/ui/card';
	import ThreadCard from './ThreadCard.svelte';

	interface Props {
		thread: Thread;
		/** Where it hangs: under its line, under a block of the story's words, or at the head of what it lost its place in. */
		hangs: CardHanging;
	}

	let { thread, hangs }: Props = $props();
	const review = useReview();

	let container: HTMLElement | undefined = $state();

	// Announced to the review, which brings the thread into view by it, never by an id on the page
	$effect(() => (container ? review.sections.registerThread(thread.id, container) : undefined));
</script>

<!-- A thread, drawn the way it is being read: folded away, or open. The keyboard is put on it when the reader is
	taken to it, whichever way it is drawn -->
<div
	bind:this={container}
	data-testid="comment-thread"
	data-thread-id={thread.id}
	class="cr-thread-hang"
	tabindex="-1"
	role="group"
	aria-label="Thread on {anchorPlace(thread.anchor)}"
>
	<ThreadCard {thread} {hangs} folded={review.threads.reading.isFolded(thread.id)} />
</div>
