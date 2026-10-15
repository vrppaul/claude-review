<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { tellsFirst } from '$lib/review/story-contents';
	import { LEFT_OUT_PART, OVERVIEW_PART } from '$lib/review/story-keys';
	import {
		threadsInTheChapter,
		threadsOnTheFileInTheChapter,
		threadsOnTheOverview,
		threadsOnWhatIsLeftOut
	} from '$lib/review/story-reading';
	import { fileStats } from '$lib/utils/file-stats';
	import { fileName } from '$lib/utils/paths';
	import ChangedLines from './ChangedLines.svelte';
	import ContentsEntry from './ContentsEntry.svelte';
	import FileRow from './FileRow.svelte';
	import SideColumn from './SideColumn.svelte';
	import {
		alsoInShort,
		chapterEntitled,
		chapterNumber,
		chaptersCounted,
		leftOutThenAndNow,
		leftOutThenAndNowSaid,
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
	// The parts above the one being read; and how many chapters of them, the overview being no chapter
	const scrolledPast = $derived(review.partsScrolledPast);
	const chaptersRead = $derived(contents.chapters.filter((chapter) => scrolledPast.has(chapter.part)).length);
	// How many changed lines no step told when the story was told, and how many none tells now: said beside what
	// is left out where the review says a round changed how many. Null otherwise, when neither is said
	const leftOutChanged = $derived(held?.moved_on?.left_out ?? null);
</script>

<!-- The story's contents, beside it: its parts down an axis, the overview and then every chapter with
	the files it tells, then what it leaves out and what the agent called housekeeping. Each file is a
	row as the tree of files draws it. Nothing while no story is held: there is nothing to find a way
	through -->
{#if held !== null}
	{@const story = held.story}
	<SideColumn
		column={review.layout.storyContents}
		landmark="nav"
		label="Story contents"
		called="the contents"
		class="bg-base-100"
		testIds={{ column: 'contents', resize: 'contents-resize', putAway: 'hide-contents', bringBack: 'show-contents' }}
	>
		{#snippet heading()}
			<h2 data-testid="contents-count" class="text-sm font-semibold">
				{chaptersCounted(contents.chapters.length, chaptersRead)}
			</h2>
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
					changed={chapter.told.changed !== null}
				>
					{#snippet node()}
						{chapterNumber(chapter.place)}
					{/snippet}
					<!-- The files of a chapter scrolled past step back, as a file the reader has finished with does. A
						chapter none of whose steps shows code any more lists none, and no empty list -->
					{#if chapter.files.length > 0}
						<ul
							data-testid="contents-files"
							class={['cr-contents-set-in', scrolledPast.has(chapter.part) && 'cr-viewed']}
						>
							{#each chapter.files as listed (listed.firstPiece.path)}
								{@const file = listed.firstPiece}
								<FileRow
									testId="contents-file"
									status={file.status}
									current={stepRead?.shown?.fileListed === listed}
									threads={threadsOnTheFileInTheChapter(chapter, listed, review.story, review.threads).length}
									title={file.path}
									onclick={() => review.sections.scrollTo(listed.opensAt)}
								>
									{#snippet name()}
										{fileName(file.path)}
									{/snippet}
									{#snippet end()}
										<!-- The file's whole change where the story first tells it; after that, where it was told -->
										{#if tellsFirst(chapter, listed)}
											<ChangedLines changed={review.story.pieces.changeOf(file.path)} />
										{:else}
											<span class="cr-faint whitespace-nowrap">{alsoInShort(listed.alsoIn)}</span>
										{/if}
									{/snippet}
								</FileRow>
							{/each}
						</ul>
					{/if}
				</ContentsEntry>
			{/each}
		</ol>

		{#if contents.leftOut.length > 0}
			<!-- Nothing can be hidden: what no step tells has its place here too, said to be outside the story -->
			<div class="cr-contents-set-in mt-2">
				<button
					type="button"
					data-testid="contents-left-out"
					class="cr-aside-row text-warning"
					aria-current={review.parts.beingRead === LEFT_OUT_PART ? 'location' : undefined}
					aria-label={leftOutChanged === null
						? undefined
						: leftOutThenAndNowSaid(leftOutChanged.when_told, leftOutChanged.now)}
					onclick={() => review.parts.goTo(LEFT_OUT_PART)}
				>
					{NOT_IN_THE_STORY}
					{#if leftOutChanged !== null}
						<!-- A round moved the code on and changed how much no step tells: how much then, and now; in
							words to whoever cannot see the arrow -->
						<span class="ml-2" aria-hidden="true">
							{leftOutThenAndNow(leftOutChanged.when_told, leftOutChanged.now)}
						</span>
					{/if}
				</button>
				<ul data-testid="contents-left-out-files">
					{#each contents.leftOut as left (left.section)}
						{@const piece = left.told.piece}
						<FileRow
							testId="contents-file"
							status={piece.status}
							current={sectionRead === left.section}
							threads={threadsOnWhatIsLeftOut(left, review.story, review.threads).length}
							title={piece.path}
							onclick={() => review.sections.scrollTo(left.section)}
						>
							{#snippet name()}
								{fileName(piece.path)}
							{/snippet}
							{#snippet end()}
								<ChangedLines changed={fileStats(piece)} />
							{/snippet}
						</FileRow>
					{/each}
				</ul>
			</div>
		{/if}

		{#if story.housekeeping.length > 0}
			<StoryHousekeeping
				paths={story.housekeeping}
				testId="contents-housekeeping"
				class="cr-contents-set-in cr-faint mt-1.5"
			/>
		{/if}
	</SideColumn>
{/if}
