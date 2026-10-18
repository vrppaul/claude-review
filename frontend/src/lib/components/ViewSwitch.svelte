<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import Icon from './Icon.svelte';
	import StoryArrivalNote from './StoryArrivalNote.svelte';
	import StoryIntroduction from './StoryIntroduction.svelte';
	import StoryOptIn from './StoryOptIn.svelte';
	import TypingIndicator from './TypingIndicator.svelte';

	const review = useReview();

	// The button of each view, as it is drawn: the keyboard goes to the one on screen, and the note of a
	// story's arrival and Story's introduction point at Story's
	const buttons: Partial<Record<ReadingViewName, HTMLButtonElement>> = $state({});

	const onScreen = $derived(review.views.onScreen.name);
	const readingFiles = $derived(onScreen === 'files');
	// What Story says beyond its name. It says it only while the files are read, where the story's own view is
	// not there to say it: that the agent is writing the story, or that one arrived and is unread until the
	// reader reads it, whether or not they put its note away
	const storySays = $derived.by(() => {
		if (!readingFiles) return null;
		if (review.story.wait?.kind === 'writing') return 'writing';
		return review.story.arrival === 'none' ? null : 'unread';
	});
	// What stands under the switch, pointing at Story: the note of a story that arrived, while the files are
	// read until the reader reads it or puts it away; else Story's introduction, which waits while the note
	// stands, its ring on Story with it
	const storyOffered = $derived(readingFiles && review.story.arrival === 'offered');
	const introducingStory = $derived(!storyOffered && review.guide.introducesStory);
	// What draws the reader to Story's segment: its introduction while the page introduces it, else a story unread
	const storyCalling = $derived.by(() => {
		if (introducingStory) return 'introduced';
		return storySays === 'unread' ? 'unread' : undefined;
	});

	// The view on screen changes from elsewhere too — the files brought on screen from where a story
	// will be — and whatever held the keyboard in the view that went goes with it. Looked at before the
	// page redraws: where something held the keyboard, and nothing does once the view is drawn, the
	// button of the view now on screen takes it. As the switch is first drawn nothing has gone
	$effect.pre(() => {
		const shown = onScreen;
		if (document.activeElement !== document.body) focusWhatRemains(() => buttons[shown]);
	});

	// The note of a story that arrived takes the introduction's place from elsewhere, and whatever held the
	// keyboard in it goes with it. Looked at before the page redraws, as the view is: Story, which both
	// point at, takes it
	$effect.pre(() => {
		if (storyOffered && document.activeElement !== document.body) focusWhatRemains(() => buttons.story);
	});

	/**
	 * The question before stories are turned on is closed. The browser gives the keyboard back to what held it
	 * as it was asked; where that is gone — the news card's Try Story — Story, which the question was about, takes it.
	 */
	function stopAsking() {
		review.wayIntoStory.stopAskingToTurnStoriesOn();
		focusWhatRemains(() => buttons.story);
	}
</script>

<!-- How the review is read, and where the reader changes it; Try Story, where Story is introduced, is the one
	other place they choose. Offered only where a story can be told: the
	review says, and nothing here asks what kind it is. The story first, as the canvas has it: an open book,
	then a stack of files. While the agent writes the story, dots that breathe stand for its book -->
{#if review.story.canBeTold}
	<div class="relative">
		<Segmented label="How to read this review" testId="reading-view">
			<Segment
				bind:element={buttons.story}
				data-testid="read-as-story"
				pressed={onScreen === 'story'}
				written={storySays === 'writing'}
				calling={storyCalling}
				onclick={() => review.wayIntoStory.readAsStory()}
			>
				{#if storySays === 'writing'}
					<TypingIndicator />
					Story · writing
				{:else}
					<Icon name="story" class="h-3.5 w-3.5" />
					Story
				{/if}
				{#if storySays === 'unread'}
					<!-- Unsaid to a screen reader: the note under the switch said it -->
					<span data-testid="segment-unread" class="text-(--cr-unread)" aria-hidden="true">●</span>
				{/if}
			</Segment>
			<Segment
				bind:element={buttons.files}
				data-testid="read-as-files"
				pressed={readingFiles}
				onclick={() => review.views.choose('files')}
			>
				<Icon name="files" class="h-3.5 w-3.5" />
				Files
			</Segment>
		</Segmented>
		{#if storyOffered}
			<StoryArrivalNote pointsAt={buttons.story} onOpen={() => review.wayIntoStory.readAsStory()} />
		{:else}
			<StoryIntroduction
				introducing={introducingStory}
				pointsAt={buttons.story}
				onTry={() => review.wayIntoStory.readAsStory()}
			/>
		{/if}
	</div>
	{#if review.wayIntoStory.askingToTurnStoriesOn}
		<StoryOptIn onTurnOn={() => review.wayIntoStory.turnStoriesOnAndRead()} onClose={stopAsking} />
	{/if}
{/if}
