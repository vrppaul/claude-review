<script lang="ts">
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import Card from '$lib/ui/Card.svelte';
	import Chip from '$lib/ui/Chip.svelte';
	import CodeBox from '$lib/ui/CodeBox.svelte';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import type { Voice } from '$lib/ui/voice';
	import { READER, THE_REVIEW } from '$lib/utils/speakers';
	import { clockTime } from '$lib/utils/time';
	import AgentAtWork from './AgentAtWork.svelte';
	import FileChip from './FileChip.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';

	// How near the bottom, in pixels, still counts as reading the newest turn
	const FOOT_SLACK = 80;
	// What attaches an agent by hand to a review started in the foreground: the review again in the background,
	// and its listening half in a loop
	const ATTACH_BY_HAND = 'claude-review diff --no-open &\nclaude-review wait --port <port> --until-event';

	interface Props {
		/**
		 * Whether the reader is at the foot of the conversation. A turn landing
		 * while they read an older one must not pull it out from under them, so
		 * only the foot follows; sending, a deliberate act, puts them back there.
		 */
		atFoot: boolean;
	}

	let { atFoot = $bindable() }: Props = $props();
	const review = useReview();

	let stream = $state<HTMLElement | null>(null);

	const attached = $derived(review.answerer.attached);
	const working = $derived(review.conversation.working);

	/** The thread a turn names, if it is still in the review. */
	function threadNamed(threadId: string | undefined) {
		return review.threads.all.find((thread) => thread.id === threadId);
	}

	/** Near enough to the bottom that the conversation should keep following. */
	function onScroll() {
		if (stream) atFoot = stream.scrollHeight - stream.scrollTop - stream.clientHeight < FOOT_SLACK;
	}

	/** Bring the newest turn into view — unless the reader scrolled away in the frame it took to lay it out. */
	function followToFoot(shown: HTMLElement) {
		if (atFoot) shown.scrollTop = shown.scrollHeight;
	}

	// A new turn is the point of the panel, so it is brought into view. The
	// count is what this watches: it changes exactly when something is said.
	$effect(() => {
		const said = review.conversation.turns.length;
		if (said === 0 || !stream || !atFoot) return;
		const shown = stream;
		requestAnimationFrame(() => followToFoot(shown));
	});
</script>

<!-- The threads a turn points at, a chip each, in the colour of whoever said it -->
{#snippet threadChips(threadIds: string[], testId: string, voice: Voice)}
	<div class="mt-2 flex flex-wrap gap-1">
		{#each threadIds as threadId (threadId)}
			{@const thread = threadNamed(threadId)}
			{#if thread}
				<Chip {voice} {testId} onclick={() => review.navigator.reveal(thread)}>
					{anchorShortPlace(thread.anchor)}
				</Chip>
			{/if}
		{/each}
	</div>
{/snippet}

<!-- A log: what the agent and the reader say is read out as it arrives, in order -->
<div
	data-testid="panel-turns"
	role="log"
	aria-label="Conversation with the agent"
	bind:this={stream}
	onscroll={onScroll}
	class="cr-scroller min-h-0 flex-1 px-3 py-3"
>
	<!-- Work showing outranks the empty state: an agent doing something
		before anybody has said anything is exactly the case a reader has
		no other way of seeing. -->
	{#if review.conversation.turns.length === 0 && !review.answerer.work}
		{#if attached}
			<div class="flex h-full flex-col justify-center">
				<EmptyNote within="view" mark="conversation" testId="panel-empty">
					Ask about anything — the plan, the tests, a file nobody commented on. A thread is about one line; this is
					about the rest.
				</EmptyNote>
			</div>
		{:else}
			<!-- Before the agent's first wait this is what the reader sees, and
				an agent that opened the review is seconds away from it. So the
				state reads as waiting; how to attach one by hand is only for
				whoever started the review themselves. -->
			<div
				data-testid="panel-unattached"
				class="flex h-full flex-col items-center justify-center gap-3 px-4 text-center"
			>
				<p class="cr-faint text-sm">The agent joins once it starts listening. Comments you write meanwhile are kept.</p>
				<details data-testid="panel-attach-by-hand" class="w-full text-left">
					<summary class="cr-faint cursor-pointer text-center text-xs"> Started the review yourself? </summary>
					<div class="mt-2 flex flex-col gap-2">
						<p class="cr-faint text-xs">
							Nothing answers a review run in the foreground. Start it in the background and keep the listening half in
							a loop:
						</p>
						<CodeBox code={ATTACH_BY_HAND} testId="attach-commands" />
					</div>
				</details>
			</div>
		{/if}
	{:else}
		<div class="flex flex-col gap-3">
			{#each review.conversation.turns as turn (turn.id)}
				{#if turn.author === THE_REVIEW}
					{@const raised = threadNamed(turn.threads?.[0])}
					<div data-testid="panel-event" class="cr-round-mark">
						<span></span>
						{#if raised}
							<!-- A thread the agent raised: the agent's arrival, in its colour -->
							<Chip voice="agent" testId="panel-thread-ref" onclick={() => review.navigator.reveal(raised)}>
								{turn.body}
							</Chip>
						{:else}
							<span class="cr-faint text-xs">{turn.body}</span>
						{/if}
						<span></span>
					</div>
				{:else if turn.author === READER}
					<!-- What the reader asked, on a card as the answer is, edged in their colour -->
					<Card tone="reader" testId="panel-said">
						<div class={[turn.cancelled && 'cr-faint']}>
							<p class="cr-who"><strong>You</strong> {clockTime(turn.at)}</p>
							{#if turn.body}
								<MarkdownRenderer text={turn.body} dense />
							{/if}
							<SaidImages images={turn.images ?? []} />
							{#if turn.threads && turn.threads.length > 0}
								{@render threadChips(turn.threads, 'panel-thread-ref', 'reader')}
							{/if}
							{#if turn.cancelled}
								<p data-testid="panel-cancelled" class="cr-faint mt-1 text-xs">
									stopped — the agent was asked to drop it
								</p>
							{/if}
						</div>
					</Card>
				{:else}
					<Card tone="quiet" testId="panel-answer">
						<p class="cr-who"><strong>Agent</strong> {clockTime(turn.at)}</p>
						<MarkdownRenderer text={turn.body} dense />
						{#if turn.threads && turn.threads.length > 0}
							<!-- Threads its words mention, drawn as the reader's mentions are -->
							{@render threadChips(turn.threads, 'answer-thread', 'agent')}
						{/if}
						{#if turn.files && turn.files.length > 0}
							<div class="mt-2 flex flex-wrap gap-1">
								<!-- Known by where they stand, since the agent may name a file twice -->
								{#each turn.files as path, position (position)}
									<FileChip {path} testId="answer-file" />
								{/each}
							</div>
						{/if}
					</Card>
				{/if}
			{/each}

			{#if working}
				<AgentAtWork since={working.at} messageId={working.id} />
			{:else if review.answerer.work}
				<!-- Work nobody is waiting on: what a round asked for, or what
					the agent took on itself. Without a row of its own it could not
					be shown at all, and a reader watching a silent panel cannot
					tell work from a hang. -->
				<AgentAtWork since={review.answerer.work.at} />
			{/if}
		</div>
	{/if}
</div>
