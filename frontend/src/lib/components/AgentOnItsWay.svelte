<script lang="ts">
	import type { Snippet } from 'svelte';
	import { tourStop, type TourTarget } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Turn from '$lib/ui/Turn.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT_STOPPED_LISTENING, TAKE_BACK } from './agent-waits';

	interface Props {
		/** Its test id, which its dots, its Take back and why that failed are known by after it. */
		testId: string;
		/** The name the tour lights it by, where the tour points at it. */
		tour?: TourTarget | undefined;
		/** How long it has been waited on, said while the agent listens: "working 3m ago". */
		waited: string;
		/** Take back what the agent is at; none where nobody asked for it. */
		takeBack?: (() => Promise<void>) | undefined;
		/** What the agent says it is doing, where it says anything. */
		children?: Snippet;
	}

	let { testId, tour, waited, takeBack, children }: Props = $props();
	const review = useReview();

	let failed = $state<string | null>(null);

	// Whether the agent is still there: once it has stopped listening the turn
	// says so, rather than go on promising what will not come
	const listening = $derived(review.answerer.attached);

	/** Take back what the agent is at, and say why where that fails; the agent decides what to do about it. */
	async function takeItBack() {
		if (!takeBack) return;
		failed = null;
		try {
			await takeBack();
		} catch (error) {
			failed = messageOf(error);
		}
	}
</script>

<!-- A turn of the agent's that has not arrived, in a thread or in the panel, is still a turn: it holds its
	place, says how long it has been waited on, so silence reads as silence rather than as something broken,
	and what the agent says it is doing -->
<Turn speaker="agent" {testId} data-tour={tour && tourStop(tour)}>
	{#snippet head()}
		{#if listening}
			<BreathingDots tone="quiet" testId="{testId}-dots" />
		{/if}
	{/snippet}
	{#snippet headEnd()}
		<span class="cr-muted">{listening ? waited : AGENT_STOPPED_LISTENING}</span>
		{#if takeBack}
			<Button tone="secondary" size="xs" testId="{testId}-take-back" onclick={takeItBack}>{TAKE_BACK}</Button>
		{/if}
	{/snippet}
	{#if failed}
		<Failure stands="apart" testId="{testId}-take-back-error" said={failed} />
	{/if}
	{@render children?.()}
</Turn>
