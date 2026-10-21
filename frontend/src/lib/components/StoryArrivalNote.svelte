<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import PassingNote from '$lib/ui/PassingNote.svelte';
	import { chaptersIn } from './story-words';

	interface Props {
		/** The control that leads to the story, which the note stands under and points at. */
		pointsAt: HTMLElement | undefined;
		/** What opening the story does: how the review is read is its to change who draws the note. */
		onOpen: () => void;
	}

	let { pointsAt, onOpen }: Props = $props();
	const review = useReview();
</script>

<!-- Said under the control that leads to a story, once one told while the reader read the files has arrived.
	Pointing at it in the colour of what is not read yet, with a bar along its foot running out as it waits;
	the view is the reader's to change: its way is the story opened, beside the note's own cross -->
<PassingNote
	{pointsAt}
	label="The story is ready"
	placement="below-start"
	arrow
	edge="unread"
	fades={false}
	testId="story-ready"
	onGone={() => review.story.putOfferAway()}
>
	{#snippet says()}
		<span>The story is ready: {chaptersIn(review.story.contents.chapters.length)}.</span>
	{/snippet}
	{#snippet main()}
		<Button tone="primary" size="sm" testId="open-story" onclick={onOpen}>Open it</Button>
	{/snippet}
</PassingNote>
