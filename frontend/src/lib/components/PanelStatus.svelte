<script lang="ts">
	import { formatWeight } from '$lib/review/weight';
	import { useReview } from '$lib/review/context';
	import { AGENT } from '$lib/utils/speakers';
	import { timeAgo } from '$lib/utils/time';
	import Icon from './Icon.svelte';

	/** How the agent stands with the review, as the dot beside its name says it. */
	type Presence = 'absent' | 'working' | 'listening';
	const DOTS: Record<Presence, string> = {
		absent: 'bg-base-300',
		working: 'bg-(--cr-mark)',
		listening: 'bg-(--cr-add-edge)'
	};

	const review = useReview();

	const attached = $derived(review.answerer.attached);
	const working = $derived(review.conversation.working);
	const presence = $derived<Presence>(!attached ? 'absent' : working ? 'working' : 'listening');
	// When the agent last said anything, so silence can be read as silence
	const lastAnswer = $derived(review.conversation.turns.findLast((turn) => turn.author === AGENT)?.at);

	/** How long ago, read off the review's clock, so it moves on while it is on screen. */
	function since(at: number): string {
		return timeAgo(at, review.clock.now);
	}

	/** How long ago the agent reported its context, if it ever has. */
	function reportedAgo(at: number | null): string {
		return at === null ? '' : since(at);
	}
</script>

<header
	data-testid="panel-status"
	class="flex h-9 shrink-0 items-center gap-2 border-b border-base-300 bg-base-200 px-3"
>
	<span class={['h-1.5 w-1.5 shrink-0 rounded-full', DOTS[presence]]}></span>
	<span class={['text-sm font-semibold', !attached && 'cr-muted']}>
		{attached ? 'Agent' : 'Waiting for the agent'}
	</span>
	{#if review.answerer.status.model}
		<span data-testid="agent-model" class="cr-faint font-mono text-xs">
			{review.answerer.status.model}
		</span>
	{/if}
	<div class="flex-1"></div>
	{#if working}
		<span class="cr-faint text-xs">{since(working.at)}</span>
	{:else if lastAnswer !== undefined}
		<span data-testid="agent-last-answer" class="cr-faint text-xs">
			answered {since(lastAnswer)}
		</span>
	{/if}
	<button
		type="button"
		data-testid="close-panel"
		class="btn btn-ghost btn-xs px-1"
		aria-label="Hide the agent panel"
		onclick={() => review.layout.agentPanel.setOpen(false)}
	>
		<Icon name="chevron" class="h-3 w-3 -rotate-90" />
	</button>
</header>

<!-- Two numbers, told apart: one this side measures, one the agent reports -->
<div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-base-300 px-3 py-1.5">
	<span data-testid="review-weight" class="cr-pill" title="What handing this review over costs">
		review {formatWeight(review.weight)}
	</span>
	{#if review.answerer.status.context}
		<span data-testid="agent-context" class="cr-pill">
			context {review.answerer.status.context} · as reported {reportedAgo(review.answerer.status.at)}
		</span>
	{/if}
</div>
