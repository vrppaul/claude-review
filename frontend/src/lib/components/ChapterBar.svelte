<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Icon from './Icon.svelte';
	import { chapterCalled, chapterNumber, stepAmong } from './story-words';

	const review = useReview();

	const contents = $derived(review.story.contents);
	// The chapter the reader is deep in: the part being read, once its head has left the area, where it is a chapter
	const chapter = $derived(contents.chapterAt(review.parts.deepIn));
	// The step being read, where the section being read is a step's
	const stepRead = $derived(contents.stepAt(review.sections.sectionInView));

	let slot: HTMLElement | undefined = $state();

	// The bar goes once the head of its chapter is back in view, as it is wherever its own buttons take the
	// reader. Looked at before the page takes the bar away: the keyboard one of its buttons holds would be
	// left on nothing, and goes to the part being read
	$effect.pre(() => {
		if (chapter === null && slot?.contains(document.activeElement)) review.parts.keyboardToBeingRead();
	});
</script>

<!-- Where the reader is, once the head of the chapter they read has scrolled away: its number and title,
	which of its steps is being read, and the ways to the chapters beside it. It stands in a slot of no
	height stuck to the top of the story's area, so the story never moves as it comes and goes -->
<div bind:this={slot} class="cr-chapter-bar-slot">
	{#if chapter !== null}
		<!-- The chapters beside it: none before the first, none after the last -->
		{@const before = contents.chapters[chapter.place - 1]}
		{@const after = contents.chapters[chapter.place + 1]}
		<div data-testid="chapter-bar" class="cr-chapter-bar">
			<div class="cr-story-measure flex h-full items-center gap-3">
				<span data-testid="chapter-bar-number" class="cr-faint text-xs">{chapterNumber(chapter.place)}</span>
				<span data-testid="chapter-bar-title" class="truncate text-sm font-semibold">{chapter.told.title}</span>
				<!-- None while why the changes belong together is read, before the first step -->
				{#if stepRead !== null && chapter.steps.includes(stepRead)}
					<span data-testid="chapter-bar-step" class="cr-muted shrink-0 text-xs">
						{stepAmong(stepRead.place, chapter.steps.length)}
					</span>
				{/if}
				<div class="flex-1"></div>
				{#if before}
					<button
						type="button"
						data-testid="go-to-chapter-before"
						class="btn shrink-0 btn-ghost btn-sm"
						onclick={() => review.parts.goTo(before.part)}
					>
						{chapterCalled(before.place)}
					</button>
				{/if}
				{#if after}
					<button
						type="button"
						data-testid="go-to-chapter-after"
						class="btn shrink-0 btn-ghost btn-sm"
						onclick={() => review.parts.goTo(after.part)}
					>
						{chapterCalled(after.place)}
						<Icon name="caret" class="h-2.5 w-2.5" />
					</button>
				{/if}
			</div>
		</div>
	{/if}
</div>
