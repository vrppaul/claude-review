<script lang="ts">
	import type { ReadingViewName } from '$lib/reader/page-layout.svelte';
	import { useReview } from '$lib/review/context';
	import Icon from './Icon.svelte';
	import type { IconName } from './icons';

	/** One way to read the review, as the switch offers it. */
	interface Offered {
		name: ReadingViewName;
		label: string;
		icon: IconName;
		testId: string;
	}

	// The story first, as the canvas has it: an open book, then a stack of files
	const OFFERED: readonly Offered[] = [
		{ name: 'story', label: 'Story', icon: 'story', testId: 'read-as-story' },
		{ name: 'files', label: 'Files', icon: 'files', testId: 'read-as-files' }
	];

	const review = useReview();
</script>

<!-- Offered only where a story can be told: the review says, and nothing here asks what kind it is -->
{#if review.story.canBeTold}
	<div data-testid="reading-view" class="cr-segmented" role="group" aria-label="How to read this review">
		{#each OFFERED as offered (offered.name)}
			<button
				type="button"
				data-testid={offered.testId}
				class="cr-segment flex items-center gap-1.5"
				aria-pressed={review.views.onScreen.name === offered.name}
				onclick={() => review.views.choose(offered.name)}
			>
				<Icon name={offered.icon} class="h-3.5 w-3.5" />
				{offered.label}
			</button>
		{/each}
	</div>
{/if}
