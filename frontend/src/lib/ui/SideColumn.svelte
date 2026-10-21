<script lang="ts">
	import type { Snippet } from 'svelte';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import Bar from './Bar.svelte';
	import { COLUMN_HOLDS, COLUMN_SIDES, type ColumnHolds, type ColumnSide, type PutAway } from './column';
	import ColumnRail from './ColumnRail.svelte';
	import EdgeGrip from './EdgeGrip.svelte';
	import Icon from './Icon.svelte';
	import IconButton from './IconButton.svelte';

	/** What the tests know each part of the column by, written whole where the column is drawn. */
	interface TestIds {
		column: string;
		head: string;
		resize: string;
		putAway: string;
		bringBack: string;
	}

	interface Props {
		/** Whether the column is on screen, and how wide the reader left it. */
		column: PutAway;
		side: ColumnSide;
		/** What the column is to whoever goes through the page by its parts: something beside what is read, or a way through it. */
		landmark: 'aside' | 'nav';
		/** What that part of the page is called: "Files". */
		label: string;
		/** What its own controls call it: "the file tree". */
		called: string;
		/** What its grip resizes, said to whoever cannot see it: "Resize the file tree". */
		resizing: string;
		/** The key that brings it back, said on its rail: `f`. */
		key: string;
		/** The name the tour lights it by, on screen or put away, written with lib/guide/tour.ts's tourStop. */
		'data-tour'?: string | undefined;
		testIds: TestIds;
		holds: ColumnHolds;
		/** What heads the column, beside the toggle that puts it away: it takes the room the toggle leaves. */
		heading: Snippet;
		/** What its rail says is behind it, once it is put away. */
		marks?: Snippet | undefined;
		children: Snippet;
		/** What stands at its foot, ruled off from what is above it: what the reader writes there. */
		foot?: Snippet | undefined;
	}

	let {
		column,
		side,
		landmark,
		label,
		called,
		resizing,
		key,
		'data-tour': tour,
		testIds,
		holds,
		heading,
		marks,
		children,
		foot
	}: Props = $props();

	const drawn = $derived(COLUMN_SIDES[side]);
	const putAway = $derived(`Put ${called} away`);
	const bringBack = $derived(`Show ${called}`);

	// The column and its toggle, while it is on screen; the rail, while it is put away
	let columnElement: HTMLElement | undefined = $state();
	let putAwayButton: HTMLButtonElement | undefined = $state();
	let rail: HTMLButtonElement | undefined = $state();

	// Put away or brought back, by its own control or by a key, the column takes with it whatever held
	// the keyboard in it: the control pressed, an entry. Looked at before the page redraws it: the
	// keyboard then goes to the control that undoes what was done, and is never left on nothing
	$effect.pre(() => {
		const open = column.open;
		const drawnBefore = open ? rail : columnElement;
		if (drawnBefore?.contains(document.activeElement)) focusWhatRemains(() => (open ? putAwayButton : rail));
	});
</script>

<!-- The toggle at the column's outer edge, drawing the column standing open -->
{#snippet toggle()}
	<IconButton
		bind:element={putAwayButton}
		tone="quiet"
		size="xs"
		shape="square"
		label={putAway}
		testId={testIds.putAway}
		onclick={() => column.toggle()}
	>
		<Icon name={drawn.open} size="sm" />
	</IconButton>
{/snippet}

<!-- The room a column stands in beside what is read, as wide as the reader left it, or as narrow as its rail once it
	is put away: the column itself, scrolling by itself, or the rail it narrows to, so the way back is where it went -->
<div
	class={['cr-ui-side-column', drawn.drawnAs, !column.open && 'cr-ui-side-column-away']}
	style:--cr-column-width="{column.width}px"
>
	{#if column.open}
		<svelte:element
			this={landmark}
			bind:this={columnElement}
			data-testid={testIds.column}
			data-tour={tour}
			aria-label={label}
			class="cr-ui-column"
		>
			<EdgeGrip {column} grows={drawn.grows} label={resizing} testId={testIds.resize} />
			<Bar heads="column" testId={testIds.head}>
				{#if drawn.toggleLeads}
					{@render toggle()}
				{/if}
				<div class="cr-ui-column-heading">{@render heading()}</div>
				{#if !drawn.toggleLeads}
					{@render toggle()}
				{/if}
			</Bar>
			<div class={COLUMN_HOLDS[holds]}>
				{@render children()}
			</div>
			{#if foot}
				<div class="cr-ui-column-foot">{@render foot()}</div>
			{/if}
		</svelte:element>
	{:else}
		<ColumnRail
			bind:element={rail}
			{side}
			label={bringBack}
			{key}
			testId={testIds.bringBack}
			data-tour={tour}
			{marks}
			onclick={() => column.toggle()}
		/>
	{/if}
</div>
