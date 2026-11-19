<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { CheckStands } from './check-row';
	import FoldChevron from './FoldChevron.svelte';
	import Icon from './Icon.svelte';
	import type { IconName, IconTone } from './icons';

	/** What a check's row draws for how it stands: its mark, in its colour where it has one, and the mark's word. */
	interface StandingLook {
		icon: IconName;
		tone: IconTone | undefined;
		said: string;
		/** The class its row is drawn with. */
		look: string;
	}

	const LOOKS: Record<CheckStands, StandingLook> = {
		failing: { icon: 'cross', tone: 'danger', said: 'failed', look: 'cr-ui-check-failed' },
		passing: { icon: 'check', tone: 'done', said: 'passed', look: 'cr-ui-check' },
		'failed-before': { icon: 'cross', tone: undefined, said: 'failed', look: 'cr-ui-check cr-ui-check-out-of-date' },
		'passed-before': { icon: 'check', tone: undefined, said: 'passed', look: 'cr-ui-check cr-ui-check-out-of-date' }
	};

	interface Props {
		stands: CheckStands;
		/** What the check is called: the tool that ran. */
		name: string;
		/** What it said in short, where it said anything. */
		said: string | null;
		/** When it was reported. */
		when: string;
		testId: string;
		/** The places a failing check failed, each a CheckFailure, where it says: under its line, which folds them. */
		failures?: Snippet | undefined;
	}

	let { stands, name, said, when, testId, failures }: Props = $props();

	const drawn = $derived(LOOKS[stands]);
	let folded = $state(false);
</script>

<!-- A kind of its own, not a Row: its mark, name, words and time are cells of the pane's one grid (CheckList), so
	each column lines up across every check, in whichever group it stands; the chevron of what it folds after the time -->
{#snippet line(folds: boolean)}
	<span class="cr-ui-check-mark">
		<Icon name={drawn.icon} size="xs" tone={drawn.tone} label={drawn.said} />
	</span>
	<span class="cr-ui-check-name">{name}</span>
	<span class={['cr-ui-check-said', stands === 'failing' && 'cr-ui-check-failing']}>{said ?? ''}</span>
	<span class="cr-ui-check-when">
		{when}
		{#if folds}<FoldChevron {folded} />{/if}
	</span>
{/snippet}

{#if stands === 'failing'}
	<li data-testid={testId} class={drawn.look}>
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
	<li data-testid={testId} class={drawn.look}>{@render line(false)}</li>
{/if}
