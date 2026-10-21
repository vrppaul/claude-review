<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
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
	the view is the reader's to change -->
<PassingNote
	{pointsAt}
	label="The story is ready"
	arrow
	edge="unread"
	fades={false}
	testId="story-ready"
	onGone={() => review.story.putOfferAway()}
>
	{#snippet children(putAway: () => void)}
		<!-- What it says, then its ways: put away for now, as any row of acts puts it off, and the story opened -->
		<div class="py-2 pr-2 pl-3 text-sm">
			<Actions testId="story-ready-actions">
				{#snippet aside()}
					<span>The story is ready: {chaptersIn(review.story.contents.chapters.length)}.</span>
				{/snippet}
				{#snippet others()}
					<IconButton tone="quiet" size="sm" shape="square" label="Close" testId="story-ready-close" onclick={putAway}>
						<Icon name="cross" size="xs" />
					</IconButton>
				{/snippet}
				{#snippet main()}
					<Button tone="primary" size="sm" testId="open-story" onclick={onOpen}>Open it</Button>
				{/snippet}
			</Actions>
		</div>
		<div data-testid="story-ready-time-left" class="cr-note-time-left" aria-hidden="true"></div>
	{/snippet}
</PassingNote>
