<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { exchangesOf } from '$lib/utils/thread-exchanges';
	import { clockTime } from '$lib/utils/time';
	import AwaitingAnswer from './AwaitingAnswer.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';
	import SuggestionDiff from './SuggestionDiff.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const exchanges = $derived(exchangesOf(thread));
	const unread = $derived(review.threads.reading.isUnread(thread.id));
	// Questions in this thread still with the agent, oldest first
	const awaiting = $derived(review.threads.reading.awaiting(thread.id));

	/** When a turn was said; a turn kept from an older version may not say. */
	function said(at: number | undefined): string {
		return at === undefined ? '' : clockTime(at);
	}

	/** When a question was handed over, if it is still waited on. */
	function askedAt(questionId: string): number | undefined {
		return awaiting.find((question) => question.id === questionId)?.at;
	}
</script>

<!-- A thread reads as a conversation: each question, and the answers held to it -->
<div class="cr-thread">
	{#each exchanges as exchange, index (exchange.id)}
		{@const waitedOn = askedAt(exchange.id)}
		{#if exchange.startsRound}
			<!-- Where one round ended and the next began, in this thread -->
			<div data-testid="round-mark" class="cr-round-mark">
				<span></span>
				<span class="cr-faint text-xs">round {exchange.round}</span>
				<span></span>
			</div>
		{/if}
		<div class="cr-exchange">
			<div>
				{#if index === 0 && raisedByAgent(thread)}
					<p class="cr-who"><strong>Agent</strong> {said(exchange.at)}</p>
				{:else if thread.turns.length > 0}
					<p class="cr-who"><strong>You</strong> {said(exchange.at)}</p>
				{/if}
				{#each splitSuggestions(exchange.asked) as part, partIndex (partIndex)}
					{#if part.kind === 'suggestion'}
						<SuggestionDiff replaced={thread.anchor.quote} suggested={part.text} />
					{:else}
						<MarkdownRenderer text={part.text} dense />
					{/if}
				{/each}
				<SaidImages images={exchange.images} />
			</div>

			{#each exchange.answers as answer, answerIndex (answer.id)}
				<div class="cr-reply">
					{#if answerIndex === 0}
						<span class="cr-tie" aria-hidden="true"></span>
					{/if}
					<div
						data-testid="thread-answer"
						data-tour="answer"
						class={['cr-answer', unread && answerIndex === exchange.answers.length - 1 && 'cr-answer-new']}
					>
						<p class="cr-who"><strong>Agent</strong> {said(answer.at)}</p>
						<MarkdownRenderer text={answer.body} dense />
					</div>
				</div>
			{/each}

			{#if waitedOn !== undefined}
				<AwaitingAnswer askedAt={waitedOn} first={exchange.answers.length === 0} />
			{/if}
		</div>
	{/each}
</div>
