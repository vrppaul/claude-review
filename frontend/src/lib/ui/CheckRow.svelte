<script lang="ts">
	import type { Snippet } from 'svelte';
	import FoldChevron from './FoldChevron.svelte';
	import Icon from './Icon.svelte';
	import type { IconName, IconTone } from './icons';

	/** How a check ended. */
	type Ended = 'passed' | 'failed';

	/** What a check's mark draws, in its tone while it is of the code on screen, and says to whoever cannot see it. */
	interface EndMark {
		icon: IconName;
		tone: IconTone;
		said: string;
	}

	const MARKS: Record<Ended, EndMark> = {
		passed: { icon: 'check', tone: 'done', said: 'passed' },
		failed: { icon: 'cross', tone: 'danger', said: 'failed' }
	};

	interface Props {
		ended: Ended;
		/** What the check is called: the tool that ran. */
		name: string;
		/** What it said in short, where it said anything. */
		said: string | null;
		/** When it was reported. */
		when: string;
		/** Whether the code changed after it ran: its mark and name step back to ink, said of code no longer on screen. */
		outOfDate: boolean;
		testId: string;
		/**
		 * The places it failed, each a CheckFailure, for a failure of the code on screen that says where: under its
		 * line, which folds them away.
		 */
		failures?: Snippet | undefined;
	}

	let { ended, name, said, when, outOfDate, testId, failures }: Props = $props();

	const mark = $derived(MARKS[ended]);
	// A failure of the code on screen is what the reader came to the pane for: a block on the error's tint
	const failingNow = $derived(ended === 'failed' && !outOfDate);
	let folded = $state(false);
</script>

<!-- Its mark, name, words and time, a column each; the chevron of what it folds after the time -->
{#snippet line(folds: boolean)}
	<span class="cr-ui-check-mark">
		<Icon name={mark.icon} size="xs" tone={outOfDate ? undefined : mark.tone} label={mark.said} />
	</span>
	<span class="cr-ui-check-name">{name}</span>
	<span class={['cr-ui-check-said', failingNow && 'cr-ui-check-failing']}>{said ?? ''}</span>
	<span class="cr-ui-check-when">
		{when}
		{#if folds}<FoldChevron {folded} />{/if}
	</span>
{/snippet}

{#if failingNow}
	<li data-testid={testId} class="cr-ui-check-failed">
		{#if failures}
			<button
				type="button"
				class="cr-ui-check cr-ui-check-fold cr-pressable"
				aria-expanded={!folded}
				onclick={() => (folded = !folded)}
			>
				{@render line(true)}
			</button>
			{#if !folded}
				<ul class="cr-ui-check-failures">
					{@render failures()}
				</ul>
			{/if}
		{:else}
			<div class="cr-ui-check">{@render line(false)}</div>
		{/if}
	</li>
{:else}
	<li data-testid={testId} class={['cr-ui-check', outOfDate && 'cr-ui-check-out-of-date']}>{@render line(false)}</li>
{/if}
