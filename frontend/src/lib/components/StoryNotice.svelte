<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { threadsNotDrawnIn } from '$lib/review/reading-view';
	import { counted, type CountedWords } from '$lib/utils/words';
	import NoticeBar from './NoticeBar.svelte';

	// What the comments a story does not draw are called where they are counted, with where they are said to be
	const COMMENTS_BEING: CountedWords = { one: 'comment is', many: 'comments are' };

	const review = useReview();

	// Whether the story held is of another take of the change than the page reads: the diff was taken again since
	const codeMovedOn = $derived(review.story.numbering === 'another-takes');
	// The threads the story draws none of: on lines no piece of it shows, or every one while the code has moved on
	const notDrawn = $derived(threadsNotDrawnIn(review.views.onScreen, review.threads));
	const firstNotDrawn = $derived(notDrawn.at(0));
	// The comments the reader was writing on lines: none is drawn against code that has moved on
	const beingWritten = $derived(review.threads.writing.openOnLines);
</script>

<!-- The way to the threads the story does not draw, while there is one: to the first of them, in the
	files, with the keyboard on it -->
{#snippet showInFiles()}
	{#if firstNotDrawn}
		<button
			type="button"
			data-testid="show-in-files"
			class="btn btn-ghost btn-xs"
			onclick={() => review.navigator.reveal(firstNotDrawn)}
		>
			Show in Files
		</button>
	{/if}
{/snippet}

<!-- What the story held says of itself, a bar above the reading area as the files' own are. With no
	story held there is nothing for anything to be off -->
{#if review.story.held !== null}
	{#if codeMovedOn}
		<!-- A state, not news, and a warning: what the story shows is no longer the code under review, so
			nothing is written on it here, and nothing of the reader's is drawn against it: where that is, is said -->
		<NoticeBar testId="story-moved-on" kind="cr-notice-moved" icon="notice" actions={showInFiles}>
			The code has changed since this story was told. It shows the code as it was, and takes no comments.
			{#if notDrawn.length > 0}
				{counted(notDrawn.length, COMMENTS_BEING)} in Files.
			{/if}
			{#if beingWritten > 0}
				{counted(beingWritten, { one: 'comment you were writing is', many: 'comments you were writing are' })} in Files.
			{/if}
		</NoticeBar>
	{:else if firstNotDrawn}
		<!-- A state, not news: the story shows part of the change, and the threads it does not draw are still in the review -->
		<NoticeBar testId="threads-off-the-story" kind="cr-notice-taken" icon="story" actions={showInFiles}>
			{counted(notDrawn.length, COMMENTS_BEING)} on lines the story does not show.
		</NoticeBar>
	{/if}
{/if}
