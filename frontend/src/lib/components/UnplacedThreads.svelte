<script lang="ts">
	import type { Thread } from '$lib/types';
	import { counted, type CountedWords } from '$lib/utils/words';
	import CommentThread from './CommentThread.svelte';

	interface Props {
		/** Threads with no line drawn to hang under. */
		threads: readonly Thread[];
		/** Why they hang here rather than under their lines, said of one thread and of several. */
		why: CountedWords;
	}

	let { threads, why }: Props = $props();
</script>

{#if threads.length > 0}
	<!-- Never off the screen: whole, with everything that can be done to them, at the head of the file or the diff they lost their lines in -->
	<div data-testid="threads-off-their-lines" class="border-b border-base-300">
		<p class="cr-muted px-4 pt-2 text-xs">{counted(threads.length, why.one, why.many)}</p>
		{#each threads as thread (thread.id)}
			<CommentThread {thread} />
		{/each}
	</div>
{/if}
