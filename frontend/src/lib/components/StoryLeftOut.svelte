<script lang="ts">
	import type { LeftOutListed } from '$lib/review/story-contents';
	import { LEFT_OUT_PART } from '$lib/review/story-keys';
	import { CHANGED_LINES, counted } from '$lib/utils/words';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import { NOT_IN_THE_STORY } from './story-words';
	import StoryPart from './StoryPart.svelte';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		/** What the story leaves out, file by file, as it lists it: the piece of each no step tells, and its section. */
		leftOut: LeftOutListed[];
	}

	let { leftOut }: Props = $props();
</script>

<!-- Nothing can be hidden: what no step tells is shown all the same, and said to be outside the story -->
<StoryPart partKey={LEFT_OUT_PART} testId="story-left-out" class="flex flex-col gap-4 border-t border-base-300 pt-6">
	{#snippet head(heading)}
		<header>
			<h2 {...heading} data-testid="part-head" class="text-base font-semibold text-warning">{NOT_IN_THE_STORY}</h2>
			<p class="cr-muted text-sm">Changed, and told by no step of the story.</p>
		</header>
	{/snippet}
	{#each leftOut as { told, section } (section)}
		<!-- A piece that cannot be drawn says so in its place, and takes no other piece down with it -->
		<svelte:boundary onerror={reportBroken}>
			<StoryPiece sectionKey={section} piece={told.piece} shows="what-no-step-tells">
				{#snippet beside()}
					{#if told.changed_lines > 0}
						<span class="cr-muted text-xs">
							{counted(told.changed_lines, CHANGED_LINES)}
						</span>
					{/if}
				{/snippet}
			</StoryPiece>
			{#snippet failed(error, retry)}
				<PartFailed what={told.piece.path} {error} {retry} />
			{/snippet}
		</svelte:boundary>
	{/each}
</StoryPart>
