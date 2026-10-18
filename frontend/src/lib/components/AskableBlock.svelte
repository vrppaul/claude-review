<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { blockKey, blockLabel, blockShortPlace } from '$lib/anchors/story';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import type { StoryBlock } from '$lib/types';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import CommentBox from './CommentBox.svelte';
	import CommentThread from './CommentThread.svelte';
	import { askComment, sayComment } from './comment-endings';

	interface Props {
		/** The block of the story's words it draws. */
		block: StoryBlock;
		/** What the block says: a comment on it quotes it. */
		words: string;
		testId: string;
		/** The block itself, as its part of the story draws it: what the story heads it with, and its words. */
		children: Snippet;
		/**
		 * The frame its words stand in where they have one of their own, as its
		 * part of the story draws it: the band stays inside the frame, and what
		 * hangs under the block hangs below it. None for a block that shares
		 * the frame of the blocks around it.
		 */
		frame?: ClassValue;
	}

	let { block, words, testId, children, frame }: Props = $props();
	const review = useReview();

	// What the offer says
	const ASK_ABOUT_THIS = 'Ask about this';
	// What stands between those words and the block's place in the offer's name
	const NAME_SEPARATOR = ': ';
	// The offer's name, for whoever cannot see which block it stands over, and told apart from every other
	// chapter's and step's: "Ask about this: ch-2 · Why"
	const name = $derived([ASK_ABOUT_THIS, blockShortPlace(block)].join(NAME_SEPARATOR));

	let asking: HTMLButtonElement | undefined = $state();

	const threads = $derived(review.threads.onBlock(block));
	// The comment being written on it, held by the review so that a reload keeps it
	const field = $derived(review.threads.writing.aboutBlock(block));
	// Whether something the reader wrote hangs open under it — a thread not folded away, or the comment being
	// written — which bands it stronger, as an open thread marks the lines it is about
	const writtenUnder = $derived(
		threads.some((thread) => !review.threads.reading.isFolded(thread.id)) || field !== undefined
	);

	// Announced to the review, which gives it the keyboard back once what hung under it goes
	$effect(() => (asking ? review.sections.registerBlock(blockKey(block), asking) : undefined));

	/** Put a comment away unsaid; the keyboard goes back to what offered it. */
	function putAway(unsaid: CommentField) {
		review.threads.writing.discard(unsaid);
		review.sections.keyboardToBlock(blockKey(block));
	}
</script>

{#snippet band()}
	<div data-testid="askable-band" class={['cr-askable', writtenUnder && 'cr-askable-written-under']}>
		{@render children()}
		<span class="cr-ask-over-block">
			<Button
				bind:element={asking}
				tone="asking"
				size="xs"
				testId="ask-about-this"
				aria-label={name}
				onclick={() => review.threads.writing.askAbout(block, words)}
			>
				<Icon name="conversation" size="xs" />
				{ASK_ABOUT_THIS}
			</Button>
		</span>
	</div>
{/snippet}

<!-- A block of the agent's words the reader may ask about, as a line is commented on: banded while it is
	pointed at, it offers "Ask about this"; what is asked hangs under it as a thread, as under a line, and
	outside any frame of the block's own -->
<div data-testid={testId} class="cr-askable-block">
	{#if frame}
		<div data-testid="askable-frame" class={frame}>
			{@render band()}
		</div>
	{:else}
		{@render band()}
	{/if}
	{#if threads.length > 0 || field !== undefined}
		<!-- What hangs under the block hangs under its band, as what hangs under a line hangs under its row: the
			band reaches below the words into the room under them, and the cards begin past it -->
		<div data-testid="askable-hangs" class="cr-askable-hangs">
			{#each threads as thread (thread.id)}
				<CommentThread {thread} />
			{/each}
			{#if field}
				<div class="cr-thread-hang">
					<CommentBox
						{field}
						onSave={() => sayComment(review, field)}
						onAsk={review.canAsk ? () => askComment(review, field) : undefined}
						onCancel={() => putAway(field)}
						label={blockLabel(block)}
					/>
				</div>
			{/if}
		</div>
	{/if}
</div>
