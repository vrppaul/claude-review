<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { threadsNotDrawnIn } from '$lib/review/reading-view';
	import Button from '$lib/ui/Button.svelte';
	import { counted, type CountedWords } from '$lib/utils/words';
	import NoticeBar from './NoticeBar.svelte';

	// What the comments a story does not draw are called where they are counted, with where they are said to be
	const COMMENTS_BEING: CountedWords = { one: 'comment is', many: 'comments are' };

	const review = useReview();

	// The threads the story draws none of: on lines no piece of it shows
	const notDrawn = $derived(threadsNotDrawnIn(review.views.onScreen, review.threads));
	const firstNotDrawn = $derived(notDrawn.at(0));
</script>

<!-- What the story held says of itself, a bar above the reading area as the files' own are: the
	threads it does not draw, while there is one, and the way to the first of them, in the files, with
	the keyboard on it. With no story held there is nothing for anything to be off. A state, not news:
	the story shows part of the change, and the threads it does not draw are still in the review -->
{#if review.story.held !== null && firstNotDrawn}
	<NoticeBar testId="threads-off-the-story" kind="cr-notice-taken" icon="story">
		{counted(notDrawn.length, COMMENTS_BEING)} on lines the story does not show.
		{#snippet actions()}
			<Button tone="quiet" size="xs" data-testid="show-in-files" onclick={() => review.navigator.reveal(firstNotDrawn)}>
				Show in Files
			</Button>
		{/snippet}
	</NoticeBar>
{/if}
