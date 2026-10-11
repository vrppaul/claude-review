<script lang="ts">
	import { anchorShortPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { fileName } from '$lib/utils/paths';
	import { READER, THE_REVIEW } from '$lib/utils/speakers';
	import { clockTime } from '$lib/utils/time';
	import AgentAtWork from './AgentAtWork.svelte';
	import Icon from './Icon.svelte';
	import MarkdownRenderer from './MarkdownRenderer.svelte';
	import SaidImages from './SaidImages.svelte';

	// How near the bottom, in pixels, still counts as reading the newest turn
	const FOOT_SLACK = 80;

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

<div data-testid="panel-turns" bind:this={stream} onscroll={onScroll} class="min-h-0 flex-1 overflow-y-auto px-3 py-3">
	<!-- Work showing outranks the empty state: an agent doing something
		before anybody has said anything is exactly the case a reader has
		no other way of seeing. -->
	{#if review.conversation.turns.length === 0 && !review.answerer.work}
		{#if attached}
			<div data-testid="panel-empty" class="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
				<Icon name="conversation" class="h-5 w-5 text-base-300" />
				<p class="cr-faint text-sm leading-relaxed">
					Ask about anything — the plan, the tests, a file nobody commented on. A thread is about one line; this is
					about the rest.
				</p>
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
				<p class="cr-faint text-sm leading-relaxed">
					The agent joins once it starts listening. Comments you write meanwhile are kept.
				</p>
				<details data-testid="panel-attach-by-hand" class="w-full text-left">
					<summary class="cr-faint cursor-pointer text-center text-xs"> Started the review yourself? </summary>
					<p class="cr-faint mt-2 text-xs leading-relaxed">
						Nothing answers a review run in the foreground. Start it in the background and keep the listening half in a
						loop:
					</p>
					<pre
						class="cr-code cr-muted mt-2 w-full overflow-x-auto rounded border border-base-300 bg-base-200 px-3 py-2">claude-review diff --no-open &
claude-review wait --port &lt;port&gt; --until-event</pre>
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
							<button
								type="button"
								data-testid="panel-thread-ref"
								class="cr-thread-chip"
								onclick={() => review.navigator.reveal(raised)}
							>
								{turn.body}
							</button>
						{:else}
							<span class="cr-faint text-xs">{turn.body}</span>
						{/if}
						<span></span>
					</div>
				{:else if turn.author === READER}
					<div data-testid="panel-said" class={['cr-panel-said rounded-r px-3 py-2', turn.cancelled && 'opacity-60']}>
						<p class="cr-who"><strong>You</strong> {clockTime(turn.at)}</p>
						{#if turn.body}
							<MarkdownRenderer text={turn.body} dense />
						{/if}
						<SaidImages images={turn.images ?? []} />
						{#if turn.threads && turn.threads.length > 0}
							<div class="mt-2 flex flex-wrap gap-1">
								{#each turn.threads as threadId (threadId)}
									{@const thread = threadNamed(threadId)}
									{#if thread}
										<button
											type="button"
											data-testid="panel-thread-ref"
											class="cr-thread-chip"
											onclick={() => review.navigator.reveal(thread)}
										>
											{anchorShortPlace(thread.anchor)}
										</button>
									{/if}
								{/each}
							</div>
						{/if}
						{#if turn.cancelled}
							<p data-testid="panel-cancelled" class="cr-faint mt-1 text-xs">
								stopped — the agent was asked to drop it
							</p>
						{/if}
					</div>
				{:else}
					<div data-testid="panel-answer" class="cr-answer">
						<p class="cr-who"><strong>Agent</strong> {clockTime(turn.at)}</p>
						<MarkdownRenderer text={turn.body} dense />
						{#if turn.files && turn.files.length > 0}
							<div class="mt-2 flex flex-wrap gap-1">
								{#each turn.files as path (path)}
									<button
										type="button"
										data-testid="answer-file"
										class="cr-thread-chip"
										onclick={() => review.sections.showFile(path)}
									>
										{fileName(path)}
									</button>
								{/each}
							</div>
						{/if}
					</div>
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
