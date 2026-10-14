<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';
	import StoryArrivalNote from './StoryArrivalNote.svelte';
	import StoryOptIn from './StoryOptIn.svelte';
	import ViewSegment from './ViewSegment.svelte';
	import { OFFERED, saidOfStory, type Said } from './view-segments';

	const review = useReview();

	// The segment of each view, as it is drawn
	const segments: Partial<Record<ReadingViewName, HTMLElement>> = $state({});
	// Whether the reader is being asked before stories are turned on
	let askedToTurnStoriesOn = $state(false);

	const onScreen = $derived(review.views.onScreen.name);
	// What each segment says beyond its name. The files say nothing more; the story does only while the
	// reader reads the files, where its own view is not there to say it
	const readingFiles = $derived(onScreen === 'files');
	const said: Record<ReadingViewName, Said> = $derived({
		story: readingFiles ? saidOfStory(review.story) : 'nothing',
		files: 'nothing'
	});
	// Whether a story that arrived is offered under the switch: while the files are read, until the reader
	// reads it or puts the offer away
	const storyOffered = $derived(readingFiles && review.story.arrival === 'offered');

	// What a press on each segment does
	const READ: Record<ReadingViewName, () => void> = { story: readAsStory, files: readByFiles };

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

	function readByFiles() {
		review.views.choose('files');
	}

	/** The reader said yes: stories are on from now, this review's is asked for, and where it will be comes on screen. */
	function turnStoriesOnAndRead() {
		void review.turnStoriesOn();
		review.views.choose('story');
	}
</script>

<!-- How the review is read, and the one place that changes it. Offered only where a story can be told: the
	review says, and nothing here asks what kind it is -->
{#if review.story.canBeTold}
	<div class="relative">
		<div data-testid="reading-view" class="cr-segmented" role="group" aria-label="How to read this review">
			{#each OFFERED as offered (offered.name)}
				<ViewSegment
					{offered}
					onScreen={onScreen === offered.name}
					says={said[offered.name]}
					onPress={READ[offered.name]}
					bind:segment={segments[offered.name]}
				/>
			{/each}
		</div>
		{#if storyOffered}
			<StoryArrivalNote pointsAt={segments.story} onOpen={readAsStory} />
		{/if}
	</div>
	{#if askedToTurnStoriesOn}
		<StoryOptIn onTurnOn={turnStoriesOnAndRead} onClose={() => (askedToTurnStoriesOn = false)} />
	{/if}
{/if}
