<script lang="ts">
	import { focusWhatCarries } from '$lib/dom/keyboard';
	import { formatWeight } from '$lib/review/weight';
	import { useReview } from '$lib/review/context';
	import ColumnBar from '$lib/ui/ColumnBar.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import { AGENT } from '$lib/utils/speakers';
	import { timeAgo } from '$lib/utils/time';
	import { PANEL_TOGGLE_ROLE } from './keymap';
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

	/** How long ago the agent reported its context, if it ever has. */
	function reportedAgo(at: number | null): string {
		return at === null ? '' : since(at);
	}

	/**
	 * The panel goes, and the button pressed with it: the keyboard goes to
	 * the header's button that brings the panel back.
	 */
	function putAway() {
		review.layout.agentPanel.setOpen(false);
		focusWhatCarries(PANEL_TOGGLE_ROLE);
	}
</script>

<ColumnBar testId="panel-status">
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
	<IconButton tone="quiet" size="xs" label="Hide the agent panel" testId="close-panel" onclick={putAway}>
		<Icon name="chevron" size="xs" pointing="right" />
	</IconButton>
</ColumnBar>

<!-- Two numbers, told apart: one this side measures, one the agent reports -->
<div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-base-300 px-3 py-1.5">
	<span data-testid="review-weight" class="cr-pill" title="What handing this review over costs">
		review {formatWeight(review.weight)} tokens
	</span>
	{#if review.answerer.status.context}
		<span data-testid="agent-context" class="cr-pill">
			context {review.answerer.status.context} · as reported {reportedAgo(review.answerer.status.at)}
		</span>
	{/if}
</div>
