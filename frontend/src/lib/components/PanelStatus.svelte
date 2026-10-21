<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { AGENT } from '$lib/utils/speakers';
	import { timeAgo } from '$lib/utils/time';
	import PresenceDot from './PresenceDot.svelte';

	const review = useReview();

	const attached = $derived(review.answerer.attached);
	const working = $derived(review.conversation.working);
	// When the agent last said anything, so silence can be read as silence
	const lastAnswer = $derived(review.conversation.turns.findLast((turn) => turn.author === AGENT)?.at);

	/** How long ago, read off the review's clock, so it moves on while it is on screen. */
	function since(at: number): string {
		return timeAgo(at, review.clock.now);
	}
</script>

<!-- What heads the agent's column: whether the agent is there, which model it is, and how long ago it last said
	anything or began what it is at -->
<PresenceDot />
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
	<!-- Said, not answered: much of what the agent says, nobody asked for -->
	<span data-testid="agent-last-answer" class="cr-faint text-xs">
		said {since(lastAnswer)}
	</span>
{/if}
