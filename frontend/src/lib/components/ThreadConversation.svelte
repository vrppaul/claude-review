<script lang="ts">
	import type { Thread } from '$lib/types';
	import { anchorOutdated, anchorQuoteReads, anchorReplaces, anchorWrittenAgainst } from '$lib/anchors/views';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import type { InSightOnTheCard } from '$lib/review/thread-reading.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import KeptQuote from '$lib/ui/KeptQuote.svelte';
	import TakenBack from '$lib/ui/TakenBack.svelte';
	import Turn from '$lib/ui/Turn.svelte';
	import TurnAside from '$lib/ui/TurnAside.svelte';
	import TurnsFold from '$lib/ui/TurnsFold.svelte';
	import { AGENT, READER } from '$lib/utils/speakers';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { drawnTurnsOf, exchangesOf, runsOf, type DrawnTurn, type Exchange } from '$lib/utils/thread-exchanges';
	import { timeAgo } from '$lib/utils/time';
	import AgentOnItsWay from './AgentOnItsWay.svelte';
	import { ASK_AGENT_NOW, ASKED_TO_DROP_IT, NOBODY_LISTENING } from './agent-waits';
	import CommentBox from './CommentBox.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';
	import SuggestionDiff from './SuggestionDiff.svelte';
	import { threadVoice, TURN_VOICES } from './thread-voice';
	import TurnMenu from './TurnMenu.svelte';

	// What the copy kept of what a thread lost its place in says it is
	const WRITTEN_AGAINST = 'Written against';

	interface Props {
		thread: Thread;
		/** Hand over everything said so far, from the reader's last turn. */
		onAsk: () => void;
		/** Why it could not be handed over, said under the words it was asked about; none while nothing failed. */
		askFailed: string | null;
	}

	let { thread, onAsk, askFailed }: Props = $props();
	const review = useReview();

	const exchanges = $derived(exchangesOf(thread));
	const drawn = $derived(drawnTurnsOf(exchanges));
	const runs = $derived(runsOf(drawn, review.threads.reading.turnsFolded(thread.id)));
	// Who spoke last: after an answer there is nothing new to hand over until the reader says something. On a
	// thread the agent raised, the opening is already the agent's word
	const lastWord = $derived(thread.turns.at(-1)?.author ?? thread.raised_by);
	// What a suggestion in the thread replaces: what the comment was written on
	const replaced = $derived(anchorReplaces(thread.anchor));
	// What it was written against, kept for when the place it hangs on is gone, and how that reads
	const writtenAgainst = $derived(anchorWrittenAgainst(thread.anchor));
	const quoteReads = $derived(anchorQuoteReads(thread.anchor));
	// Questions in this thread still with the agent, oldest first
	const awaiting = $derived(review.threads.reading.awaiting(thread.id));
	// Whether words of the reader's in it are being rewritten, which asking now would hand over as they were
	const rewriting = $derived(exchanges.some((exchange) => review.threads.writing.edit(thread.id, exchange.id)));
	// Whether what the reader said last is theirs to hand over: nothing waited on, the last word theirs, and none of
	// their words being rewritten
	const yoursToAsk = $derived(awaiting.length === 0 && lastWord !== AGENT && !rewriting);
	const inSight = $derived<InSightOnTheCard>({
		rewriting: (turnId: string) => review.threads.writing.edit(thread.id, turnId) !== undefined,
		askFailed: askFailed !== null
	});

	// Earlier turns fold as the thread is drawn with none folded; drawn again, as its file comes near, it keeps its fold
	$effect.pre(() => review.threads.reading.foldAsDrawn(thread, inSight));

	/** Fold the earlier turns again, worked out anew; the keyboard stays on the row's button, or with the thread. */
	function hideEarlierTurns() {
		review.threads.reading.foldEarlierTurns(thread, inSight);
		review.sections.keyboardToThread(thread.id);
	}

	/** Take a question back; its turn of the agent's goes, and the keyboard stays with the thread. */
	async function takeBackAndStay(questionId: string) {
		await review.threads.takeBack(thread.id, questionId);
		review.sections.keyboardToThread(thread.id);
	}

	/** The rewriting is over, its words saved or put away; the keyboard stays with the thread. */
	function editDone(done: () => void) {
		done();
		review.sections.keyboardToThread(thread.id);
	}

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
	still awaited. A long one folds what lies between the comment that opened it and its last turns behind one row,
	which shows them again. A turn kept from an older version may not say when it was said. What the thread hangs on
	and what can be done to it stand on its card's bar (ThreadBar); in the first turn, over its words, stands what an
	outdated thread was written against. What the reader said and the agent has not been handed is theirs to
	rewrite, where it stands, or to delete, from the menu at the head of its turn -->
<!-- Each run of turns known by its first, so a row the reader pressed stays the same row, the keyboard on it -->
{#each runs as run (run.turns[0].id)}
	{#if run.folded}
		<TurnsFold
			count={run.turns.length}
			open={run.open}
			onShow={() =>
				review.threads.reading.showFoldedTurns(
					thread.id,
					run.turns.map((turn) => turn.id)
				)}
			onHide={hideEarlierTurns}
			testId="earlier-turns"
		>
			{#each run.turns as turn (turn.id)}
				{@render rowsOf(turn)}
			{/each}
		</TurnsFold>
	{:else}
		{#each run.turns as turn (turn.id)}
			{@render rowsOf(turn)}
		{/each}
	{/if}
{/each}

<!-- The rows a turn draws: a question, or an answer; after the last of its exchange, the answer still awaited -->
{#snippet rowsOf(turn: DrawnTurn)}
	{#if turn.kind === 'question'}
		{@render question(turn.exchange)}
	{:else}
		{@const answeredAt = turn.answer.at}
		<Turn
			speaker="agent"
			testId="thread-answer"
			data-tour={tourStop('answer')}
			landing={review.threads.reading.isNewAnswer(thread.id, turn.id)}
		>
			{#snippet head()}
				{#if answeredAt !== undefined}
					<span>answered {howLongAgo(answeredAt)}</span>
				{/if}
			{/snippet}
			<MarkdownRenderer text={turn.answer.body} dense />
		</Turn>
	{/if}
	{#if turn.endsExchange}
		{@render awaited(turn.exchange)}
	{/if}
{/snippet}

{#snippet question(exchange: Exchange)}
	{@const takenBackAt = review.threads.reading.takenBackAt(thread.id, exchange.id)}
	<!-- The first question is the comment that opened the thread; the last, what the reader said last -->
	{@const opening = exchange === exchanges[0]}
	{@const last = exchange === exchanges.at(-1)}
	{@const editing = review.threads.writing.edit(thread.id, exchange.id)}
	{@const handed = review.threads.handing.has(thread.id, exchange.id)}
	<!-- Asking stands at the last words while none of the thread's are being rewritten; the menu, at no words that are -->
	{@const asks = last && yoursToAsk}
	{@const rewritable = exchange.by === READER && !handed && editing === undefined}
	{#if exchange.startsRound}
		<!-- Where one round ended and the next began, in this thread -->
		<TurnAside lays="across" testId="round-mark">
			<span class="cr-faint text-xs">round {exchange.round}</span>
		</TurnAside>
	{/if}
	<!-- What stands at the far end of the turn's head: asking the agent, at what the reader said last, and the menu -->
	{#snippet turnEnd()}
		{#if asks}
			{@render askingNow()}
		{/if}
		{#if rewritable}
			<TurnMenu {thread} saidId={exchange.id} />
		{/if}
	{/snippet}
	<Turn
		speaker={TURN_VOICES[exchange.by]}
		testId="thread-question"
		takenBack={takenBackAt !== undefined}
		headEnd={asks || rewritable ? turnEnd : undefined}
	>
		{#snippet head()}
			{#if exchange.at !== undefined}
				<span>{howLongAgo(exchange.at)}</span>
			{/if}
		{/snippet}
		{#if opening && anchorOutdated(thread.anchor) && writtenAgainst.length > 0}
			<!-- One that has lost its place keeps its own copy of what was there -->
			<KeptQuote caption={WRITTEN_AGAINST} lines={writtenAgainst} reads={quoteReads} testId="written-against" />
		{/if}
		{#if editing}
			<!-- Its words are the field they are rewritten in; the comment's with what it asks for, which is the
				thread's. Handed to the agent meanwhile, they can no longer be saved over -->
			<CommentBox
				field={editing}
				onSave={() => editDone(() => review.threads.say(editing))}
				onCancel={() => editDone(() => review.threads.writing.discard(editing))}
				severityPicker={opening}
				hangs="in-its-thread"
				voice={threadVoice(thread)}
			/>
		{:else}
			{#each splitSuggestions(exchange.asked) as part, partIndex (partIndex)}
				{#if part.kind === 'suggestion'}
					<SuggestionDiff {replaced} suggested={part.text} />
				{:else}
					<MarkdownRenderer text={part.text} dense />
				{/if}
			{/each}
			<SaidImages images={exchange.images} />
			{#if last && askFailed}
				<Failure stands="apart" testId="ask-error" said={askFailed} />
			{/if}
		{/if}
	</Turn>
	{#if takenBackAt !== undefined}
		<TakenBack ago={howLongAgo(takenBackAt)} said={ASKED_TO_DROP_IT} testId="thread-taken-back" />
	{/if}
{/snippet}

<!-- The answer still awaited after a question: the agent's turn, on its way -->
{#snippet awaited(exchange: Exchange)}
	{@const waitedOn = askedAt(exchange.id)}
	{#if waitedOn !== undefined}
		<AgentOnItsWay
			testId="awaiting-answer"
			tour="awaited-answer"
			waited={`asked ${howLongAgo(waitedOn)}`}
			takeBack={() => takeBackAndStay(exchange.id)}
		/>
	{/if}
{/snippet}

<!-- At the head of what the reader said last, while it is theirs to hand over: the way to hand it over now, or, with
	no agent there to hear it, where it goes instead. With the review not reached, neither -->
{#snippet askingNow()}
	{#if review.canAsk}
		<Button tone="asking" size="xs" testId="ask-now-thread" onclick={onAsk}>
			<Icon name="conversation" size="xs" />
			{ASK_AGENT_NOW}
		</Button>
	{:else if !review.answerer.attached}
		<span data-testid="ask-hint" class="cr-muted text-xs">{NOBODY_LISTENING}</span>
	{/if}
{/snippet}
