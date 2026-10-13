<script lang="ts">
	import { LEFT_OUT_PART } from '$lib/review/story-contents';
	import { leftOutSectionKey } from '$lib/review/story-pieces';
	import type { LeftOut } from '$lib/types';
	import { counted } from '$lib/utils/words';
	import { reportBroken } from './broken-parts';
	import PartFailed from './PartFailed.svelte';
	import { NOT_IN_THE_STORY } from './story-words';
	import StoryPart from './StoryPart.svelte';
	import StoryPiece from './StoryPiece.svelte';

	interface Props {
		/** What the story leaves out, file by file: the piece of each no step tells. */
		leftOut: LeftOut[];
	}

	let { leftOut }: Props = $props();
</script>

<!-- Nothing can be hidden: what no step tells is shown all the same, and said to be outside the story -->
<StoryPart
	partKey={LEFT_OUT_PART}
	label={NOT_IN_THE_STORY}
	testId="story-left-out"
	class="flex flex-col gap-4 border-t border-base-300 pt-6"
>
	<header>
		<h2 class="text-base font-semibold text-warning">{NOT_IN_THE_STORY}</h2>
		<p class="cr-muted text-sm">Changed, and told by no step of the story.</p>
	</header>
	{#each leftOut as left (leftOutSectionKey(left))}
		<!-- A piece that cannot be drawn says so in its place, and takes no other piece down with it -->
		<svelte:boundary onerror={reportBroken}>
			<StoryPiece sectionKey={leftOutSectionKey(left)} piece={left.piece} shows="what-no-step-tells">
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
</StoryPart>
