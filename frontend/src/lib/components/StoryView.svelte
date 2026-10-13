<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { threadsNotDrawnIn } from '$lib/review/reading-view';
	import { leftOutSectionKey, stepSectionKey } from '$lib/review/story-reading';
	import type { Thread, ToldStep, ToldStory } from '$lib/types';
	import { counted } from '$lib/utils/words';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import StoryPiece from './StoryPiece.svelte';

	// What joins the first line of a step to its last, and a chapter's number to a step's
	const RANGE_DASH = '–';
	const NUMBER_SEPARATOR = '.';
	// What each list of the overview is headed by, in the order they are drawn
	const OVERVIEW_LISTS = [
		{ field: 'decisions', heading: 'Decided, and why' },
		{ field: 'turned_down', heading: 'Turned down' },
		{ field: 'later', heading: 'Left for later' }
	] as const;

	const review = useReview();

	const held = $derived(review.story.held);
	const numbering = $derived(review.story.numbering);
	// Whether the story held is of another take of the change than the page reads: the diff was taken again since
	const codeMovedOn = $derived(numbering === 'another-takes');
	// The threads the story draws none of: on lines no piece of it shows, or every one while the code has moved on
	const notDrawn = $derived(threadsNotDrawnIn(review.views.onScreen, review.threads));
	const firstNotDrawn = $derived(notDrawn.at(0));

	let container: HTMLElement | undefined = $state();

	// The story reports which piece is being read, as the files' view does of its files
	$effect(() => {
		if (!container) return;
		return review.sections.watchInView(container);
	});

	/** A step's lines as its heading says them: "42", or "42–47". */
	function linesOf(step: ToldStep): string {
		const { first, last } = step.lines;
		return first === last ? String(first) : `${first}${RANGE_DASH}${last}`;
	}

	/** A step as the story numbers it: its chapter's number, then its own. */
	function numberOf(chapterPlace: number, stepPlace: number): string {
		return `${chapterPlace + 1}${NUMBER_SEPARATOR}${stepPlace + 1}`;
	}

	/**
	 * The chapter something leads to, as the reader knows it: by its number.
	 * The review refuses a story that leads to a chapter it does not have.
	 */
	function chapterNamed(story: ToldStory, id: string): string {
		return `chapter ${story.chapters.findIndex((chapter) => chapter.id === id) + 1}`;
	}
</script>

<!-- The way to the threads the story does not draw: to the first of them, in the files, with the keyboard on it -->
{#snippet showInFiles(first: Thread)}
	<button
		type="button"
		data-testid="show-in-files"
		class="btn btn-ghost btn-xs"
		onclick={() => review.navigator.reveal(first)}
	>
		Show in Files
	</button>
{/snippet}

<!-- The same change, read as the agent tells it: one scroll, the overview first, then every chapter in a row -->
<main bind:this={container} data-testid="story-view" class="cr-diff-area bg-base-100">
	{#if held === null}
		<p data-testid="no-story" class="cr-muted px-4 py-8 text-center text-sm">
			No story has been told of this change yet. The agent that made it tells one with
			<code class="font-mono">claude-review story</code>.
		</p>
	{:else}
		{@const story = held.story}
		<article class="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-8">
			<header class="flex flex-wrap items-baseline gap-3">
				<h1 data-testid="story-title" class="text-xl font-semibold">{story.title}</h1>
				<span data-testid="story-round" class="cr-muted text-xs">Round {held.round}</span>
				{#if story.told_from === 'commits'}
					<span data-testid="story-reconstructed" class="text-xs text-(--cr-agent)">reconstructed</span>
				{/if}
			</header>

			{#if story.told_from === 'commits'}
				<p class="border-l-2 border-dashed border-(--cr-agent) pl-4 text-sm">
					The agent did not make this change. The reasons below are its reading of the code and of the commit messages,
					not what was decided at the time.
				</p>
			{/if}

			{#if codeMovedOn}
				<!-- A state, not news, and a warning: what the story shows is no longer the code under review, so
					nothing is written on it here, and nothing of the reader's is drawn against it: where that is, is said -->
				<div
					data-testid="story-moved-on"
					class="cr-notice cr-notice-moved flex items-center gap-3 rounded px-3 py-1.5 text-xs"
				>
					<span>
						The code has changed since this story was told. It shows the code as it was, and takes no comments.
						{#if notDrawn.length > 0}
							{counted(notDrawn.length, 'comment is', 'comments are')} in Files.
						{/if}
						{#if review.threads.writing.openOnLines > 0}
							{counted(
								review.threads.writing.openOnLines,
								'comment you were writing is',
								'comments you were writing are'
							)} in Files.
						{/if}
					</span>
					<div class="flex-1"></div>
					{#if firstNotDrawn}
						{@render showInFiles(firstNotDrawn)}
					{/if}
				</div>
			{:else if firstNotDrawn}
				<!-- A state, not news: the story shows part of the change, and the threads it does not draw are still in the review -->
				<div
					data-testid="threads-off-the-story"
					class="cr-notice cr-notice-taken flex items-center gap-3 rounded px-3 py-1.5 text-xs"
				>
					<span>
						{counted(notDrawn.length, 'comment is', 'comments are')} on lines the story does not show.
					</span>
					<div class="flex-1"></div>
					{@render showInFiles(firstNotDrawn)}
				</div>
			{/if}

			<!-- The agent's voice carries its colour down the edge; what to doubt is a warning, and says so in yellow -->
			<section
				data-testid="story-overview"
				aria-label="The change in short"
				class="grid grid-cols-[4rem_minmax(0,1fr)] gap-x-4 gap-y-3 border-l-2 border-(--cr-agent) pl-5"
			>
				<span class="cr-muted pt-0.5 text-xs">Task</span>
				<p>{story.overview.task}</p>
				<span class="cr-muted pt-0.5 text-xs">Done</span>
				<p>{story.overview.done}</p>
				{#if story.overview.doubt}
					<span class="pt-0.5 text-xs font-semibold text-warning">Doubt</span>
					<p data-testid="story-doubt">{story.overview.doubt}</p>
				{/if}
			</section>

			{#if story.overview.diagram}
				<!-- Drawn as its source until the page draws diagrams: nothing of what the agent sent is kept from the reader -->
				<figure data-testid="story-diagram" class="flex flex-col gap-2">
					{#if story.overview.diagram.caption}
						<figcaption class="cr-muted text-xs">{story.overview.diagram.caption}</figcaption>
					{/if}
					<pre class="overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2 font-mono text-xs">{story
							.overview.diagram.mermaid}</pre>
				</figure>
			{/if}

			{#if OVERVIEW_LISTS.some((list) => story.overview[list.field].length > 0)}
				<details data-testid="story-more">
					<summary class="cursor-pointer text-sm">More about this change</summary>
					<div class="mt-3 flex flex-col gap-4 border-l-2 border-(--cr-agent) pl-5">
						{#each OVERVIEW_LISTS as list (list.field)}
							{#if story.overview[list.field].length > 0}
								<section>
									<h2 class="cr-muted text-xs font-semibold">{list.heading}</h2>
									<ul class="mt-1 flex list-disc flex-col gap-1 pl-5 text-sm">
										{#each story.overview[list.field] as item, itemPlace (itemPlace)}
											<li>
												{item.text}
												{#if item.chapter}
													<span class="cr-muted text-xs">— {chapterNamed(story, item.chapter)}</span>
												{/if}
											</li>
										{/each}
									</ul>
								</section>
							{/if}
						{/each}
					</div>
				</details>
			{/if}

			{#each story.chapters as chapter, chapterPlace (chapter.id)}
				<section data-testid="story-chapter" class="flex flex-col gap-5 border-t border-base-300 pt-6">
					<header class="flex items-baseline gap-3">
						<span class="cr-muted text-sm">{chapterPlace + 1}</span>
						<h2 data-testid="chapter-title" class="text-lg font-semibold">{chapter.title}</h2>
						<span class="cr-faint ml-auto text-xs">{counted(chapter.steps.length, 'step', 'steps')}</span>
					</header>
					<p data-testid="chapter-why" class="border-l-2 border-(--cr-agent) pl-4">{chapter.why}</p>
					{#if chapter.doubt}
						<p data-testid="chapter-doubt" class="rounded-r border-l-2 border-warning bg-(--cr-warning-tint) px-3 py-2">
							<span class="block text-xs font-semibold text-warning">Where to doubt</span>
							{chapter.doubt}
						</p>
					{/if}

					{#each chapter.steps as step, stepPlace (stepPlace)}
						<div data-testid="story-step" class="flex flex-col gap-2">
							<!-- The reason above the code, never beside it: the code and the panel need the width -->
							<div class="flex gap-3 border-l-2 border-(--cr-agent) pl-3">
								<span data-testid="step-number" class="pt-0.5 font-mono text-xs text-(--cr-agent)">
									{numberOf(chapterPlace, stepPlace)}
								</span>
								{#if step.reason}
									<p data-testid="step-reason" class="min-w-0">{step.reason}</p>
								{/if}
							</div>
							<!-- A piece that cannot be drawn says so in its place, and takes no other piece down with it -->
							<svelte:boundary onerror={reportBroken}>
								<StoryPiece
									sectionKey={stepSectionKey(chapterPlace, stepPlace)}
									piece={step.piece}
									shows="a-step"
									{numbering}
									scrollRoot={container ?? null}
								>
									{#snippet beside()}
										<span data-testid="step-lines" class="cr-muted font-mono text-xs">{linesOf(step)}</span>
									{/snippet}
								</StoryPiece>
								{#snippet failed(error, retry)}
									<PartFailed what={step.file} {error} {retry} />
								{/snippet}
							</svelte:boundary>
						</div>
					{/each}
				</section>
			{/each}

			{#if story.left_out.length > 0}
				<!-- Nothing can be hidden: what no step tells is shown all the same, and said to be outside the story -->
				<section data-testid="story-left-out" class="flex flex-col gap-4 border-t border-base-300 pt-6">
					<header>
						<h2 class="text-base font-semibold text-warning">Not in the story</h2>
						<p class="cr-muted text-sm">Changed, and told by no step of the story.</p>
					</header>
					{#each story.left_out as left, place (left.piece.path)}
						<svelte:boundary onerror={reportBroken}>
							<StoryPiece
								sectionKey={leftOutSectionKey(place)}
								piece={left.piece}
								shows="what-no-step-tells"
								{numbering}
								scrollRoot={container ?? null}
							>
								{#snippet beside()}
									{#if left.changed_lines > 0}
										<span class="cr-muted text-xs">
											{counted(left.changed_lines, 'changed line', 'changed lines')}
										</span>
									{/if}
								{/snippet}
							</StoryPiece>
							{#snippet failed(error, retry)}
								<PartFailed what={left.piece.path} {error} {retry} />
							{/snippet}
						</svelte:boundary>
					{/each}
				</section>
			{/if}

			{#if story.housekeeping.length > 0}
				<details data-testid="story-housekeeping" class="cr-muted border-t border-base-300 pt-6 text-sm">
					<summary class="cursor-pointer">
						Housekeeping · {counted(story.housekeeping.length, 'file', 'files')}
					</summary>
					<ul class="mt-2 flex flex-col gap-0.5 font-mono text-xs">
						{#each story.housekeeping as path (path)}
							<li>{path}</li>
						{/each}
					</ul>
				</details>
			{/if}
		</article>
	{/if}
</main>
