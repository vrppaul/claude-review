<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';
	import Icon from './Icon.svelte';
	import StoryArrivalNote from './StoryArrivalNote.svelte';
	import StoryIntroduction from './StoryIntroduction.svelte';
	import StoryOptIn from './StoryOptIn.svelte';
	import TypingIndicator from './TypingIndicator.svelte';

	// The classes both buttons carry: a segment of the switch, its icon and its words in a row
	const SEGMENT_CLASSES = 'cr-segment flex items-center gap-1.5';

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
	// Whether a story that arrived is offered under the switch: while the files are read, until the reader
	// reads it or puts the offer away
	const storyOffered = $derived(readingFiles && review.story.arrival === 'offered');
	// Whether Story is introduced under the switch now: the note of a story's arrival stands there first
	const introducingStory = $derived(!storyOffered && review.guide.introducesStory);

	// The view on screen changes from elsewhere too — the files brought on screen from where a story
	// will be — and whatever held the keyboard in the view that went goes with it. Looked at before the
	// page redraws: where something held the keyboard, and nothing does once the view is drawn, the
	// button of the view now on screen takes it. As the switch is first drawn nothing has gone
	$effect.pre(() => {
		const shown = onScreen;
		if (document.activeElement !== document.body) focusWhatRemains(() => buttons[shown]);
	});
</script>

<!-- How the review is read, and where the reader changes it; Try Story, where Story is introduced, is the one
	other place they choose. Offered only where a story can be told: the
	review says, and nothing here asks what kind it is. The story first, as the canvas has it: an open book,
	then a stack of files. While the agent writes the story, dots that breathe stand for its book -->
{#if review.story.canBeTold}
	<div class="relative">
		<div data-testid="reading-view" class="cr-segmented" role="group" aria-label="How to read this review">
			<button
				bind:this={buttons.story}
				type="button"
				data-testid="read-as-story"
				class={[
					SEGMENT_CLASSES,
					storySays === 'writing' && 'cr-segment-writing',
					storySays === 'unread' && 'cr-segment-unread',
					introducingStory && 'cr-segment-introduced'
				]}
				aria-pressed={onScreen === 'story'}
				onclick={() => review.readAsStory()}
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
			</button>
			<button
				bind:this={buttons.files}
				type="button"
				data-testid="read-as-files"
				class={SEGMENT_CLASSES}
				aria-pressed={readingFiles}
				onclick={() => review.views.choose('files')}
			>
				<Icon name="files" class="h-3.5 w-3.5" />
				Files
			</button>
		</div>
		{#if storyOffered}
			<StoryArrivalNote pointsAt={buttons.story} onOpen={() => review.readAsStory()} />
		{:else}
			<StoryIntroduction pointsAt={buttons.story} onTry={() => review.readAsStory()} />
		{/if}
	</div>
	{#if review.askingToTurnStoriesOn}
		<StoryOptIn onTurnOn={() => review.turnStoriesOnAndRead()} onClose={() => review.stopAskingToTurnStoriesOn()} />
	{/if}
{/if}
