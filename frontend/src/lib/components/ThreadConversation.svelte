<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorQuoteReads, anchorReplaces, anchorWrittenAgainst } from '$lib/anchors/views';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
	import Turn from '$lib/ui/Turn.svelte';
	import TurnAside from '$lib/ui/TurnAside.svelte';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { exchangesOf } from '$lib/utils/thread-exchanges';
	import { timeAgo } from '$lib/utils/time';
	import AgentOnItsWay from './AgentOnItsWay.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';
	import SuggestionDiff from './SuggestionDiff.svelte';
	import ThreadActions from './ThreadActions.svelte';
	import ThreadHeading from './ThreadHeading.svelte';
	import { TURN_VOICES } from './thread-voice';

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
	still awaited. A turn kept from an older version may not say when it was said. The head of the first
	turn says what the thread hangs on and holds what can be done to it, and under it stands what an
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
			{#if opening}
				<ThreadHeading {thread} />
			{/if}
		{/snippet}
		{#snippet headEnd()}
			{#if opening}
				<ThreadActions {thread} />
			{/if}
		{/snippet}
		{#if opening && thread.anchor.outdated && writtenAgainst.length > 0}
			<!-- One that has lost its place keeps its own copy of what was there -->
			<div class="my-1">
				<EdgeFrame tone="stale" ground="tint" testId="stale-quote">
					<p class="cr-muted mb-1 text-xs">what it was written against</p>
					{#each writtenAgainst as line, lineIndex (lineIndex)}
						{#if quoteReads === 'code'}
							<pre class="cr-code cr-muted overflow-x-auto font-mono">{line}</pre>
						{:else}
							<p class="cr-muted">{line}</p>
						{/if}
					{/each}
				</EdgeFrame>
			</div>
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
