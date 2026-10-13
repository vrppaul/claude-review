<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { threadsNotDrawnIn } from '$lib/review/reading-view';
	import type { Thread } from '$lib/types';
	import { counted } from '$lib/utils/words';
	import Icon from './Icon.svelte';

	const review = useReview();

	// Whether the story held is of another take of the change than the page reads: the diff was taken again since
	const codeMovedOn = $derived(review.story.numbering === 'another-takes');
	// The threads the story draws none of: on lines no piece of it shows, or every one while the code has moved on
	const notDrawn = $derived(threadsNotDrawnIn(review.views.onScreen, review.threads));
	const firstNotDrawn = $derived(notDrawn.at(0));
	// The comments the reader was writing on lines: none is drawn against code that has moved on
	const beingWritten = $derived(review.threads.writing.openOnLines);
</script>

<!-- The way to the threads the story does not draw: to the first of them, in the files, with the keyboard on it -->
{#snippet showInFiles(first: Thread)}
	<button
		type="button"
		data-testid="show-in-files"
		class="btn btn-ghost btn-xs"
		onclick={() => review.navigator.reveal(first)}
	>
		Show in Files
	</button>
{/snippet}

<!-- What the story held says of itself, a bar above the reading area as the files' own are: it stands
	however far down the story the reader is. With no story held there is nothing for anything to be off -->
{#if review.story.held !== null}
	{#if codeMovedOn}
		<!-- A state, not news, and a warning: what the story shows is no longer the code under review, so
			nothing is written on it here, and nothing of the reader's is drawn against it: where that is, is said -->
		<div
			data-testid="story-moved-on"
			class="cr-notice cr-notice-moved flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
		>
			<Icon name="notice" class="h-3 w-3 shrink-0" />
			<span>
				The code has changed since this story was told. It shows the code as it was, and takes no comments.
				{#if notDrawn.length > 0}
					{counted(notDrawn.length, 'comment is', 'comments are')} in Files.
				{/if}
				{#if beingWritten > 0}
					{counted(beingWritten, 'comment you were writing is', 'comments you were writing are')} in Files.
				{/if}
			</span>
			<div class="flex-1"></div>
			{#if firstNotDrawn}
				{@render showInFiles(firstNotDrawn)}
			{/if}
		</div>
	{:else if firstNotDrawn}
		<!-- A state, not news: the story shows part of the change, and the threads it does not draw are still in the review -->
		<div
			data-testid="threads-off-the-story"
			class="cr-notice cr-notice-taken flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
		>
			<Icon name="story" class="h-3 w-3 shrink-0" />
			<span>
				{counted(notDrawn.length, 'comment is', 'comments are')} on lines the story does not show.
			</span>
			<div class="flex-1"></div>
			{@render showInFiles(firstNotDrawn)}
		</div>
	{/if}
{/if}
