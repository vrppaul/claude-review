<script lang="ts">
	import type { Snippet } from 'svelte';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import Actions from './Actions.svelte';
	import Icon from './Icon.svelte';
	import IconButton from './IconButton.svelte';
	import { arrowOffsetTo, type PaneEdge, type Placement } from './pane';
	import PopoverPanel from './PopoverPanel.svelte';

	/**
	 * How its time runs out:
	 * - fading: it fades as its time runs out, and says and offers what it does, handed the way to put it away
	 * - lasting: whole until its time is out, which a bar along its foot shows; it says its words in a row of acts,
	 *   its own cross among them and the act it leads to last, where it leads to one
	 */
	type Lasts =
		| { fades: true; children: Snippet<[putAway: () => void]>; says?: never; main?: never }
		| { fades: false; says: Snippet; main?: Snippet | undefined; children?: never };

	type Props = Lasts & {
		/** The control the note stands under, which the keyboard goes back to as the note goes. */
		pointsAt: HTMLElement | undefined;
		/** What the note is called, said to whoever cannot see it. */
		label: string;
		/** Which of the control's edges it lines up with, as a pane opened from there would. */
		placement: Placement;
		/** Whether it points at the control: a note that is not about it does not. */
		arrow: boolean;
		/** What it says by its edge, where it says anything by it. */
		edge?: PaneEdge | undefined;
		testId: string;
		/** Called once the note goes, by itself or as it is put away, for whoever drew it to stop drawing it. */
		onGone: () => void;
	};

	// How long a note stands before it puts itself away, the mouse over it or not. Whatever shows the time
	// running out reads it as --cr-note-lasts; the note goes by this clock, not by what shows it, which
	// runs for no reader who asked for less motion
	const STANDS_FOR_MS = 4_000;

	let { pointsAt, label, placement, arrow, edge, testId, onGone, ...lasts }: Props = $props();

	let pane: HTMLDivElement | undefined = $state();
	// How far in from the edge it lines up with the note points at the control, where it draws an arrow
	const arrowOffset = $derived(arrowOffsetTo(pointsAt));

	// Started as the note is drawn, and let go with it: put away before, it puts nothing away
	$effect(() => {
		const timer = setTimeout(putAway, STANDS_FOR_MS);
		return () => clearTimeout(timer);
	});

	/** Put the note away. The keyboard it held, if it held it, goes to the control it stands under. */
	function putAway() {
		if (pane?.contains(document.activeElement)) focusWhatRemains(() => pointsAt);
		onGone();
	}
</script>

<!-- The way a lasting note is put away for now, as any row of acts puts a thing off -->
{#snippet cross()}
	<IconButton tone="quiet" size="sm" shape="square" label="Close" testId="{testId}-close" onclick={putAway}>
		<Icon name="cross" size="xs" />
	</IconButton>
{/snippet}

<!-- Said under a control by the page, of something that happened: a note, and no popover, for it opens from no
	control and takes the keyboard from nothing the reader is doing. It lies over what is under it, so it goes
	by itself in a few seconds, or at once as it is put away -->
<div class="contents" style:--cr-note-lasts="{STANDS_FOR_MS}ms">
	<PopoverPanel
		bind:pane
		role="status"
		{label}
		{placement}
		width="fitted"
		{arrow}
		{arrowOffset}
		{edge}
		fading={lasts.fades}
		{testId}
	>
		{#if lasts.fades}
			{@render lasts.children(putAway)}
		{:else}
			<div class="py-2 pr-2 pl-3 text-sm">
				<Actions testId="{testId}-actions" aside={lasts.says} others={cross} main={lasts.main} />
			</div>
			<div data-testid="{testId}-time-left" class="cr-ui-note-time-left" aria-hidden="true"></div>
		{/if}
	</PopoverPanel>
</div>
