<script lang="ts">
	import type { Thread } from '$lib/types';
	import { counted, type CountedWords } from '$lib/utils/words';
	import CommentThread from './CommentThread.svelte';

	interface Props {
		/** Threads with nothing drawn to hang under: no line, or no block of the story. */
		threads: readonly Thread[];
		/** Why they hang here rather than under what they were written on, said of one thread and of several. */
		why: CountedWords;
	}

	let { threads, why }: Props = $props();
</script>

{#if threads.length > 0}
	<!-- Never off the screen: whole, with everything that can be done to them, at the head of the file, the
		diff or the story they lost their place in -->
	<div data-testid="unplaced-threads" class="border-b border-base-300">
		<p class="cr-muted px-4 pt-2 text-xs">{counted(threads.length, why)}</p>
		{#each threads as thread (thread.id)}
			<CommentThread {thread} hangs="head" />
		{/each}
	</div>
{/if}
