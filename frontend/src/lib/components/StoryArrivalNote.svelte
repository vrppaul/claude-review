<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Icon from './Icon.svelte';
	import PassingNote from './PassingNote.svelte';
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
	the view is the reader's to change -->
<PassingNote
	{pointsAt}
	label="The story is ready"
	data-testid="story-ready"
	class="cr-popover-unread"
	onGone={() => review.story.putOfferAway()}
>
	{#snippet children(putAway: () => void)}
		<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 pr-2 pl-3.5 text-sm">
			<span>The story is ready: {chaptersIn(review.story.contents.chapters.length)}.</span>
			<Button tone="primary" size="xs" data-testid="open-story" onclick={onOpen}>Open it</Button>
			<IconButton tone="quiet" size="xs" label="Close" data-testid="story-ready-close" onclick={putAway}>
				<Icon name="cross" />
			</IconButton>
		</div>
		<div data-testid="story-ready-time-left" class="cr-note-time-left" aria-hidden="true"></div>
	{/snippet}
</PassingNote>
