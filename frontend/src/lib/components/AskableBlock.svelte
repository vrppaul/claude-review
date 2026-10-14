<script lang="ts">
	import type { Snippet } from 'svelte';
	import { blockKey, blockLabel } from '$lib/anchors/story';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import type { StoryBlock } from '$lib/types';
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
	}

	let { block, words, testId, children }: Props = $props();
	const review = useReview();

	let asking: HTMLButtonElement | undefined = $state();

	const threads = $derived(review.threads.onBlock(block));
	// The comment being written on it, held by the review so that a reload keeps it
	const field = $derived(review.threads.writing.aboutBlock(block));

	// Announced to the review, which gives it the keyboard back once what hung under it goes
	$effect(() => (asking ? review.sections.registerBlock(blockKey(block), asking) : undefined));

	/** Put a comment away unsaid; the keyboard goes back to what offered it. */
	function putAway(unsaid: CommentField) {
		review.threads.writing.discard(unsaid);
		review.sections.keyboardToBlock(blockKey(block));
	}
</script>

<!-- A block of the agent's words the reader may ask about, as a line is commented on: banded while it is
	pointed at, it offers "Ask about this"; what is asked hangs under it as a thread, as under a line -->
<div data-testid={testId}>
	<div data-testid="askable-band" class={['cr-askable', (threads.length > 0 || field) && 'cr-askable-held']}>
		{@render children()}
		<button
			bind:this={asking}
			type="button"
			data-testid="ask-about-this"
			class="cr-ask"
			onclick={() => review.threads.writing.askAbout(block, words)}
		>
			<svg
				width="13"
				height="13"
				viewBox="0 0 16 16"
				fill="none"
				stroke="currentColor"
				stroke-width="1.4"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z" />
			</svg>
			Ask about this
		</button>
	</div>
	{#each threads as thread (thread.id)}
		<CommentThread {thread} />
	{/each}
	{#if field}
		<div class="px-3 py-2">
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
