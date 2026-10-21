<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorQuoteReads, anchorReplaces, anchorWrittenAgainst } from '$lib/anchors/views';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import KeptQuote from '$lib/ui/KeptQuote.svelte';
	import Turn from '$lib/ui/Turn.svelte';
	import TurnAside from '$lib/ui/TurnAside.svelte';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { exchangesOf } from '$lib/utils/thread-exchanges';
	import { timeAgo } from '$lib/utils/time';
	import AgentOnItsWay from './AgentOnItsWay.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';
	import SuggestionDiff from './SuggestionDiff.svelte';
	import { TURN_VOICES } from './thread-voice';

	// What the copy kept of what a thread lost its place in says it is
	const WRITTEN_AGAINST = 'Written against';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
	const review = useReview();

	const exchanges = $derived(exchangesOf(thread));
	// What a suggestion in the thread replaces: what the comment was written on
	const replaced = $derived(anchorReplaces(thread.anchor));
	// What it was written against, kept for when the place it hangs on is gone, and how that reads
	const writtenAgainst = $derived(anchorWrittenAgainst(thread.anchor));
	const quoteReads = $derived(anchorQuoteReads(thread.anchor));
	// Questions in this thread still with the agent, oldest first
	const awaiting = $derived(review.threads.reading.awaiting(thread.id));

	/** How long ago a turn was said, by the review's clock, which ticks while it is drawn. */
	function howLongAgo(at: number): string {
		return timeAgo(at, review.clock.now);
	}

	/** When a question was handed over, if it is still waited on. */
	function askedAt(questionId: string): number | undefined {
		return awaiting.find((question) => question.id === questionId)?.at;
	}
</script>

<!-- A thread reads as a conversation, a turn to a row: each question, the answers held to it, and the answer
	still awaited. A turn kept from an older version may not say when it was said. What the thread hangs on and
	what can be done to it stand on its card's bar (ThreadBar); in the first turn, over its words, stands what an
	outdated thread was written against -->
{#each exchanges as exchange, index (exchange.id)}
	{@const waitedOn = askedAt(exchange.id)}
	<!-- The first question is the comment that opened the thread -->
	{@const opening = index === 0}
	{#if exchange.startsRound}
		<!-- Where one round ended and the next began, in this thread -->
		<TurnAside lays="across" testId="round-mark">
			<span class="cr-faint text-xs">round {exchange.round}</span>
		</TurnAside>
	{/if}
	<Turn speaker={TURN_VOICES[exchange.by]} testId="thread-question">
		{#snippet head()}
			{#if exchange.at !== undefined}
				<span>{howLongAgo(exchange.at)}</span>
			{/if}
		{/snippet}
		{#if opening && thread.anchor.outdated && writtenAgainst.length > 0}
			<!-- One that has lost its place keeps its own copy of what was there -->
			<KeptQuote caption={WRITTEN_AGAINST} lines={writtenAgainst} reads={quoteReads} testId="written-against" />
		{/if}
		{#each splitSuggestions(exchange.asked) as part, partIndex (partIndex)}
			{#if part.kind === 'suggestion'}
				<SuggestionDiff {replaced} suggested={part.text} />
			{:else}
				<MarkdownRenderer text={part.text} dense />
			{/if}
		{/each}
		<SaidImages images={exchange.images} />
	</Turn>

	{#each exchange.answers as answer (answer.id)}
		<Turn
			speaker="agent"
			testId="thread-answer"
			data-tour={tourStop('answer')}
			landing={review.threads.reading.isNewAnswer(thread.id, answer.id)}
		>
			{#snippet head()}
				{#if answer.at !== undefined}
					<span>answered {howLongAgo(answer.at)}</span>
				{/if}
			{/snippet}
			<MarkdownRenderer text={answer.body} dense />
		</Turn>
	{/each}

	{#if waitedOn !== undefined}
		<!-- The answer still awaited: the agent's turn, on its way -->
		<AgentOnItsWay
			testId="awaiting-answer"
			tour="awaited-answer"
			waited={`asked ${howLongAgo(waitedOn)} — keep reading, the answer lands here`}
			takeBack={() => review.threads.takeBack(thread.id, exchange.id)}
		/>
	{/if}
{/each}
