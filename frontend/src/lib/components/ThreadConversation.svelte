<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorReplaces } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { AGENT } from '$lib/utils/speakers';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { exchangesOf } from '$lib/utils/thread-exchanges';
	import { timeAgo } from '$lib/utils/time';
	import AwaitingAnswer from './AwaitingAnswer.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';
	import SuggestionDiff from './SuggestionDiff.svelte';
	import ThreadTurn from './ThreadTurn.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const exchanges = $derived(exchangesOf(thread));
	// What a suggestion in the thread replaces: what the comment was written on
	const replaced = $derived(anchorReplaces(thread.anchor));
	// Questions in this thread still with the agent, oldest first
	const awaiting = $derived(review.threads.reading.awaiting(thread.id));

	/** How long ago a turn was said, by the review's clock, which ticks while it is drawn. */
	function ago(at: number): string {
		return timeAgo(at, review.clock.now);
	}

	/** When a question was handed over, if it is still waited on. */
	function askedAt(questionId: string): number | undefined {
		return awaiting.find((question) => question.id === questionId)?.at;
	}
</script>

<!-- A thread reads as a conversation, a turn to a row: each question, the answers held to it, and the answer
	still awaited. A turn kept from an older version may not say when it was said -->
{#each exchanges as exchange (exchange.id)}
	{@const waitedOn = askedAt(exchange.id)}
	{#if exchange.startsRound}
		<!-- Where one round ended and the next began, in this thread -->
		<div data-testid="round-mark" class="cr-thread-row cr-thread-aside cr-round-mark">
			<span></span>
			<span class="cr-faint text-xs">round {exchange.round}</span>
			<span></span>
		</div>
	{/if}
	<ThreadTurn voice={exchange.by} testId="thread-question">
		{#snippet head()}
			{#if exchange.at !== undefined}
				<span>{ago(exchange.at)}</span>
			{/if}
		{/snippet}
		{#each splitSuggestions(exchange.asked) as part, partIndex (partIndex)}
			{#if part.kind === 'suggestion'}
				<SuggestionDiff {replaced} suggested={part.text} />
			{:else}
				<MarkdownRenderer text={part.text} dense />
			{/if}
		{/each}
		<SaidImages images={exchange.images} />
	</ThreadTurn>

	{#each exchange.answers as answer (answer.id)}
		<ThreadTurn
			voice={AGENT}
			testId="thread-answer"
			tour="answer"
			landing={review.threads.reading.isNewAnswer(thread.id, answer.id)}
		>
			{#snippet head()}
				{#if answer.at !== undefined}
					<span>answered {ago(answer.at)}</span>
				{/if}
			{/snippet}
			<MarkdownRenderer text={answer.body} dense />
		</ThreadTurn>
	{/each}

	{#if waitedOn !== undefined}
		<AwaitingAnswer threadId={thread.id} questionId={exchange.id} askedAt={waitedOn} />
	{/if}
{/each}
