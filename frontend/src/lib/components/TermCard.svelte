<script lang="ts">
	import { blockLabel, type ChapterBlock, type OverviewBlock } from '$lib/anchors/story';
	import type { OverviewText } from '$lib/types';
	import type { WashedTone } from '$lib/ui/card';
	import Heading from '$lib/ui/Heading.svelte';
	import type { HeadingTone } from '$lib/ui/heading';
	import type { IconName } from '$lib/ui/icons';
	import Tile from '$lib/ui/Tile.svelte';
	import type { TileTone } from '$lib/ui/tile';
	import AskableBlock from './AskableBlock.svelte';

	/** How a kind of thing a story says in short is drawn: in a tone of its own, and the mark on its card's tile. */
	interface TermLook {
		/** Whose it is, or what it is: its card, its tile and its term are drawn in it, so a tone all three have. */
		tone: WashedTone & TileTone & HeadingTone;
		mark: IconName;
	}

	// What was asked is the reader's, what was done the agent's, and what to doubt is what to look at
	const TERM_LOOKS: Record<OverviewText, TermLook> = {
		task: { tone: 'reader', mark: 'target' },
		done: { tone: 'agent', mark: 'check' },
		doubt: { tone: 'warning', mark: 'warning' }
	};

	interface Props {
		/**
		 * The block of the story's words it draws, which says what it is: what was asked, what was done, or where to
		 * doubt it, of the whole change; or where to doubt a chapter.
		 */
		block: OverviewBlock | ChapterBlock<'doubt'>;
		/** What the block says. */
		words: string;
		testId: string;
	}

	let { block, words, testId }: Props = $props();

	const look = $derived(TERM_LOOKS[block.text]);
</script>

<!-- One thing a story says in short, which the reader may ask about, on a card of its own in its colour: its mark,
	what the story heads it with, then its words. The overview's task, what was done and where to doubt it, and where
	to doubt a chapter, are drawn alike -->
<AskableBlock {block} {words} {testId} frame={{ shape: 'card', tone: look.tone }}>
	<!-- A term and what it says, as a list of them would be: the thread under it stands outside any list -->
	<div class="flex items-start gap-3">
		<Tile tone={look.tone} icon={look.mark} />
		<div class="flex max-w-(--cr-prose-measure) min-w-0 flex-1 flex-col gap-0.5">
			<Heading tag="p" heads="list" tone={look.tone} role="term">{blockLabel(block)}</Heading>
			<p role="definition" data-testid="block-words">{words}</p>
		</div>
	</div>
</AskableBlock>
