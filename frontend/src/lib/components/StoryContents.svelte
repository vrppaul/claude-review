<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { tellsFirst } from '$lib/review/story-contents';
	import { LEFT_OUT_PART, OVERVIEW_PART } from '$lib/review/story-keys';
	import { threadsInTheChapter, threadsOnTheOverview } from '$lib/review/story-reading';
	import { counted } from '$lib/utils/words';
	import ChangedLines from './ChangedLines.svelte';
	import ContentsEntry from './ContentsEntry.svelte';
	import ContentsFile from './ContentsFile.svelte';
	import SideColumn from './SideColumn.svelte';
	import {
		alsoInShort,
		chapterEntitled,
		chapterNumber,
		chaptersCounted,
		leftOutThenAndNow,
		NOT_IN_THE_STORY,
		THE_OVERVIEW
	} from './story-words';
	import StoryHousekeeping from './StoryHousekeeping.svelte';

	const review = useReview();

	const held = $derived(review.story.held);
	const contents = $derived(review.story.contents);
	// The section being read, and the step it is of, where it is a step's: the row of that step's file is lit
	const sectionRead = $derived(review.sections.sectionInView);
	const stepRead = $derived(review.stepBeingRead);
	// How many of the chapters the reader has read through: the overview is read through too, and is no chapter
	const chaptersRead = $derived(
		contents.chapters.filter((chapter) => review.story.progress.isRead(chapter.part)).length
	);
	// How many changed lines no step tells now: said beside how many none told, once a round moved the code on
	const changedLinesLeftOut = $derived(contents.leftOut.reduce((lines, left) => lines + left.told.changed_lines, 0));
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
				{chaptersCounted(contents.chapters.length, chaptersRead)}
			</span>
		{/snippet}

		<ol data-testid="contents-parts">
			<ContentsEntry
				part={OVERVIEW_PART}
				label={THE_OVERVIEW}
				title={THE_OVERVIEW}
				threads={threadsOnTheOverview(story.overview, review.threads).length}
			>
				{#snippet node()}
					<span class="cr-contents-dot"></span>
				{/snippet}
			</ContentsEntry>
			{#each contents.chapters as chapter (chapter.part)}
				<ContentsEntry
					part={chapter.part}
					label={chapterEntitled(chapter.place, chapter.told.title)}
					title={chapter.told.title}
					threads={threadsInTheChapter(chapter, review.story, review.threads).length}
					changed={chapter.changedSteps > 0}
				>
					{#snippet node()}
						{chapterNumber(chapter.place)}
					{/snippet}
					<!-- The files of a chapter read through step back, as a file the reader has finished with does -->
					<ul
						data-testid="contents-files"
						class={['cr-contents-files', review.story.progress.isRead(chapter.part) && 'cr-viewed']}
					>
						{#each chapter.files as listed (listed.firstPiece.path)}
							<ContentsFile file={listed.firstPiece} opensAt={listed.opensAt} current={stepRead?.fileListed === listed}>
								<!-- The file's whole change where the story first tells it; after that, where it was told -->
								{#if tellsFirst(chapter, listed)}
									<ChangedLines changed={review.story.pieces.changeOf(listed.firstPiece.path)} />
								{:else}
									{alsoInShort(listed.alsoIn)}
								{/if}
							</ContentsFile>
						{/each}
					</ul>
				</ContentsEntry>
			{/each}
		</ol>

		{#if contents.leftOut.length > 0}
			<!-- Nothing can be hidden: what no step tells has its place here too, said to be outside the story -->
			<button
				type="button"
				data-testid="contents-left-out"
				class="cr-contents-aside mt-2 font-semibold text-warning"
				aria-current={review.parts.beingRead === LEFT_OUT_PART ? 'location' : undefined}
				onclick={() => review.parts.goTo(LEFT_OUT_PART)}
			>
				{NOT_IN_THE_STORY}
				{#if held.moved_on !== null && held.moved_on.left_out_when_told !== changedLinesLeftOut}
					<!-- A round moved the code on and changed how much no step tells: how much then, and now -->
					<span class="ml-2">{leftOutThenAndNow(held.moved_on.left_out_when_told, changedLinesLeftOut)}</span>
				{/if}
			</button>
			<ul data-testid="contents-left-out-files" class="cr-contents-files cr-contents-files-left-out">
				{#each contents.leftOut as left (left.section)}
					{@const piece = left.told.piece}
					<ContentsFile file={piece} opensAt={left.section} current={sectionRead === left.section}>
						<!-- A file that shows no line has no hunk to count -->
						{#if piece.hunks.length > 0}
							{counted(piece.hunks.length, { one: 'hunk', many: 'hunks' })}
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
