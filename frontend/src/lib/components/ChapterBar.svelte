<script lang="ts">
	import { KEPT_IN_SIGHT_ROLE } from '$lib/dom/in-sight';
	import { useReview } from '$lib/review/context';
	import Bar from '$lib/ui/Bar.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { chapterByNumber, chapterNumber, stepAmong } from './story-words';

	const review = useReview();

	const contents = $derived(review.story.contents);
	// The chapter the reader is deep in: the part being read, once its head has left the area, where it is a chapter
	const chapter = $derived(contents.chapterAt(review.parts.deepIn));
	const stepRead = $derived(review.stepBeingRead);

	let slot: HTMLElement | undefined = $state();

	// The bar goes once the head of its chapter is back in view, as it is wherever its own buttons take the
	// reader. Looked at before the page takes the bar away: the keyboard one of its buttons holds would be
	// left on nothing, and goes to the head of the part being read
	$effect.pre(() => {
		if (chapter === null && slot?.contains(document.activeElement)) review.parts.keyboardToBeingRead();
	});
</script>

<!-- Where the reader is, once the head of the chapter they read has scrolled away: its number and title,
	which of its steps is being read, and the ways to the chapters beside it. It stands in a slot kept in
	sight at the top of the story's area, and takes no room there, so the story never moves as it comes
	and goes -->
<div bind:this={slot} data-role={KEPT_IN_SIGHT_ROLE} class="cr-chapter-bar-slot">
	{#if chapter !== null}
		<!-- The chapters beside it: none before the first, none after the last -->
		{@const before = contents.chapters[chapter.place - 1]}
		{@const after = contents.chapters[chapter.place + 1]}
		<!-- The room the story keeps for the bar over its top, which the bar fills -->
		<div data-testid="chapter-bar-room" class="cr-chapter-bar-room">
			<Bar heads="chapter" testId="chapter-bar">
				<div class="cr-story-gutter flex min-w-0 flex-1 items-center gap-3">
					<span data-testid="chapter-bar-number" class="cr-chapter-number text-xs">{chapterNumber(chapter.place)}</span>
					<span data-testid="chapter-bar-title" class="truncate text-sm font-semibold">{chapter.told.title}</span>
					<!-- None while why the changes belong together is read, before the first step -->
					{#if stepRead !== null && chapter.steps.includes(stepRead)}
						<span data-testid="chapter-bar-step" class="cr-muted shrink-0 text-xs">
							{stepAmong(stepRead.place, chapter.steps.length)}
						</span>
					{/if}
					<div class="flex-1"></div>
					{#if before}
						<Button tone="quiet" size="sm" testId="go-to-chapter-before" onclick={() => review.parts.goTo(before.part)}>
							<Icon name="chevron" size="xs" pointing="left" />
							{chapterByNumber(before.place)}
						</Button>
					{/if}
					{#if after}
						<Button tone="quiet" size="sm" testId="go-to-chapter-after" onclick={() => review.parts.goTo(after.part)}>
							{chapterByNumber(after.place)}
							<Icon name="chevron" size="xs" pointing="right" />
						</Button>
					{/if}
				</div>
			</Bar>
		</div>
	{/if}
</div>
