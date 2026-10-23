<script lang="ts">
	import type { Snippet } from 'svelte';
	import { blockKey, blockLabel, blockShortPlace } from '$lib/anchors/story';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import type { StoryBlock } from '$lib/types';
	import Band from '$lib/ui/Band.svelte';
	import Button from '$lib/ui/Button.svelte';
	import type { FrameLook } from '$lib/ui/frame';
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
		 * Where its words stand, as its part of the story draws them: in none,
		 * on the edge of the part they stand in; on a card of their own, which
		 * its band fills and what hangs under the block hangs below; as an item
		 * of a list on a card of lists; or as the top line of a frame of code.
		 */
		frame: FrameLook;
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
	// Whether anything hangs under it, open or folded away
	const hangsSomething = $derived(review.threads.hangsUnder(block));

	// Announced to the review, which gives it the keyboard back once what hung under it goes
	$effect(() => (asking ? review.sections.registerBlock(blockKey(block), asking) : undefined));

	/** Put a comment away unsaid; the keyboard goes back to what offered it. */
	function putAway(unsaid: CommentField) {
		review.threads.writing.discard(unsaid);
		review.sections.keyboardToBlock(blockKey(block));
	}
</script>

{#snippet offer()}
	<Button
		bind:element={asking}
		tone="asking"
		size="xs"
		testId="ask-about-this"
		aria-label={name}
		title={ASK_ABOUT_THIS}
		wordsGivingWay={ASK_ABOUT_THIS}
		onclick={() => review.threads.writing.askAbout(block, words)}
	>
		<Icon name="conversation" size="xs" />
	</Button>
{/snippet}

<!-- What is asked about it hangs under it as a thread, as under a line, and outside any frame of its own -->
{#snippet hung()}
	{#each threads as thread (thread.id)}
		<CommentThread {thread} hangs="block" />
	{/each}
	{#if field}
		<div class="cr-thread-hang">
			<CommentBox
				{field}
				onSave={() => sayComment(review, field)}
				onAsk={review.canAsk ? () => askComment(review, field) : undefined}
				onCancel={() => putAway(field)}
				label={blockLabel(block)}
				hangs="block"
			/>
		</div>
	{/if}
{/snippet}

<!-- A block of the agent's words the reader may ask about, as a line is commented on: banded while it is
	pointed at, it offers "Ask about this" -->
<Band current={writtenUnder} {frame} {testId} {offer} under={hangsSomething ? hung : undefined}>
	{@render children()}
</Band>
