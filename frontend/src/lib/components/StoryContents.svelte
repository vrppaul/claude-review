<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { LEFT_OUT_PART, OVERVIEW_PART } from '$lib/review/story-contents';
	import { leftOutSectionKey } from '$lib/review/story-pieces';
	import { counted } from '$lib/utils/words';
	import ChangedLines from './ChangedLines.svelte';
	import ContentsEntry from './ContentsEntry.svelte';
	import ContentsFile from './ContentsFile.svelte';
	import SideColumn from './SideColumn.svelte';
	import { alsoInShort, chapterEntitled, chapterNumber, NOT_IN_THE_STORY, THE_OVERVIEW } from './story-words';
	import StoryHousekeeping from './StoryHousekeeping.svelte';

	const review = useReview();

	const held = $derived(review.story.held);
	const contents = $derived(review.story.contents);
	// The section being read, and the step it is of, where it is a step's: the row of that step's file is lit
	const sectionRead = $derived(review.sections.sectionInView);
	const stepRead = $derived(sectionRead === null ? null : contents.stepAt(sectionRead));
</script>

<!-- The story's contents, beside it: its parts down an axis, the overview and then every chapter with
	the files it tells, then what it leaves out and what the agent called housekeeping. Nothing while
	no story is held: there is nothing to find a way through -->
{#if held !== null}
	{@const story = held.story}
	<SideColumn
		column={review.layout.storyContents}
		landmark="nav"
		label="Story contents"
		called="the contents"
		class="bg-base-200"
		testIds={{ column: 'contents', resize: 'contents-resize', putAway: 'hide-contents', bringBack: 'show-contents' }}
	>
		{#snippet heading()}
			<h2 class="text-sm font-semibold">Story</h2>
			<span data-testid="contents-count" class="cr-faint text-xs">
				{counted(contents.chapters.length, 'chapter', 'chapters')}
			</span>
		{/snippet}

		<ol>
			<ContentsEntry part={OVERVIEW_PART} label={THE_OVERVIEW} title={THE_OVERVIEW}>
				{#snippet node()}
					<span class="cr-contents-dot"></span>
				{/snippet}
			</ContentsEntry>
			{#each contents.chapters as chapter (chapter.part)}
				<ContentsEntry
					part={chapter.part}
					label={chapterEntitled(chapter.place, chapter.told.title)}
					title={chapter.told.title}
				>
					{#snippet node()}
						{chapterNumber(chapter.place)}
					{/snippet}
					<ul class="cr-contents-files">
						{#each chapter.files as listed (listed.file.path)}
							<ContentsFile file={listed.file} opensAt={listed.opensAt} current={stepRead?.file === listed}>
								<!-- The file's whole change where the story first tells it; after that, where it was told -->
								{#if listed.firstToldHere}
									<ChangedLines changed={listed.change} />
								{:else}
									{alsoInShort(listed.alsoIn)}
								{/if}
							</ContentsFile>
						{/each}
					</ul>
				</ContentsEntry>
			{/each}
		</ol>

		{#if story.left_out.length > 0}
			<!-- Nothing can be hidden: what no step tells has its place here too, said to be outside the story -->
			<button
				type="button"
				data-testid="contents-left-out"
				class="cr-contents-aside mt-2 font-semibold text-warning"
				aria-current={review.parts.beingRead === LEFT_OUT_PART ? 'location' : undefined}
				onclick={() => review.parts.goTo(LEFT_OUT_PART)}
			>
				{NOT_IN_THE_STORY}
			</button>
			<ul class="cr-contents-files cr-contents-files-left-out">
				{#each story.left_out as left (leftOutSectionKey(left))}
					{@const section = leftOutSectionKey(left)}
					<ContentsFile file={left.piece} opensAt={section} current={sectionRead === section}>
						<!-- A file that shows no line has no hunk to count -->
						{#if left.piece.hunks.length > 0}
							{counted(left.piece.hunks.length, 'hunk', 'hunks')}
						{/if}
					</ContentsFile>
				{/each}
			</ul>
		{/if}

		{#if story.housekeeping.length > 0}
			<StoryHousekeeping
				paths={story.housekeeping}
				testId="contents-housekeeping"
				class="cr-contents-aside cr-faint mt-1.5"
			/>
		{/if}
	</SideColumn>
{/if}
