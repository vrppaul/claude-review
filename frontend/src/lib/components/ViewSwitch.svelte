<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';
	import Icon from './Icon.svelte';
	import { arrowOffsetTo } from './pane-placement';
	import PopoverPanel from './PopoverPanel.svelte';
	import StoryOptIn from './StoryOptIn.svelte';
	import { chaptersIn } from './story-words';
	import TypingIndicator from './TypingIndicator.svelte';

	const review = useReview();

	// The segment of each view, as it is drawn
	const segments: Partial<Record<ReadingViewName, HTMLElement>> = $state({});
	// Whether the reader is being asked before stories are turned on
	let askedToTurnStoriesOn = $state(false);

	const onScreen = $derived(review.views.onScreen.name);
	// What the switch says of a story the reader is not looking at, while they read the files: that it is
	// being written, or that it has arrived and waits to be read
	const readingFiles = $derived(onScreen === 'files');
	const writing = $derived(readingFiles && review.story.wait?.kind === 'writing');
	const arrived = $derived(readingFiles && review.story.arrivedUnseen);
	// The switch, which the note of a story's arrival stands under, its left edge on the switch's
	let around: HTMLElement | undefined = $state();
	// How far in from that edge the note points at the Story segment
	const noteArrowOffset = $derived(arrived && segments.story ? arrowOffsetTo(segments.story) : 0);
	// How far from the left of the window the note stands, as it is drawn: it is no wider than the window
	// has room for from there, so on a narrow screen its words wrap, and nothing of it is cut off
	const noteStandsAt = $derived(arrived && around ? around.getBoundingClientRect().left : 0);

	// The view on screen changes from elsewhere too — the files brought on screen from where a story
	// will be — and whatever held the keyboard in the view that went goes with it. Looked at before the
	// page redraws: where something held the keyboard, and nothing does once the view is drawn, the
	// segment of the view now on screen takes it. As the switch is first drawn nothing has gone
	$effect.pre(() => {
		const shown = onScreen;
		if (document.activeElement !== document.body) focusWhatRemains(() => segments[shown]);
	});

	/** Read the review as its story; where that means having one written, the reader is asked first. */
	function readAsStory() {
		if (review.storyViewOpens) review.views.choose('story');
		else askedToTurnStoriesOn = true;
	}

	/** The reader said yes: stories are on from now, this review's is asked for, and where it will be comes on screen. */
	function turnStoriesOnAndRead() {
		void review.turnStoriesOn();
		review.views.choose('story');
	}
</script>

<!-- Offered only where a story can be told: the review says, and nothing here asks what kind it is. The
	story first, as the canvas has it: an open book, then a stack of files -->
{#if review.story.canBeTold}
	<div bind:this={around} class="relative" style:--cr-note-stands-at="{noteStandsAt}px">
		<div data-testid="reading-view" class="cr-segmented" role="group" aria-label="How to read this review">
			<button
				bind:this={segments.story}
				type="button"
				data-testid="read-as-story"
				class={[
					'cr-segment flex items-center gap-1.5',
					writing && 'cr-segment-writing',
					arrived && 'cr-segment-unread'
				]}
				aria-pressed={onScreen === 'story'}
				onclick={readAsStory}
			>
				{#if writing}
					<TypingIndicator />
					Story · writing
				{:else}
					<Icon name="story" class="h-3.5 w-3.5" />
					Story
				{/if}
				{#if arrived}
					<!-- Unsaid to a screen reader: the note under the switch says it -->
					<span data-testid="story-arrived" class="text-(--cr-unread)" aria-hidden="true">●</span>
				{/if}
			</button>
			<button
				bind:this={segments.files}
				type="button"
				data-testid="read-as-files"
				class="cr-segment flex items-center gap-1.5"
				aria-pressed={onScreen === 'files'}
				onclick={() => review.views.choose('files')}
			>
				<Icon name="files" class="h-3.5 w-3.5" />
				Files
			</button>
		</div>
		{#if arrived}
			<!-- A note, and no popover: it opens from no control, and takes the keyboard from nothing the reader
				is doing. The view is theirs to change -->
			<PopoverPanel
				role="status"
				label="The story is ready"
				placement="below-start"
				arrowOffset={noteArrowOffset}
				data-testid="story-ready"
				class="cr-popover-note cr-popover-unread"
			>
				<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 pr-2 pl-3.5 text-sm">
					<span>The story is ready: {chaptersIn(review.story.contents.chapters.length)}.</span>
					<button
						type="button"
						data-testid="open-story"
						class="btn btn-primary btn-xs"
						onclick={() => review.views.choose('story')}
					>
						Open it
					</button>
				</div>
			</PopoverPanel>
		{/if}
	</div>
	{#if askedToTurnStoriesOn}
		<StoryOptIn onTurnOn={turnStoriesOnAndRead} onClose={() => (askedToTurnStoriesOn = false)} />
	{/if}
{/if}
