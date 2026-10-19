<script lang="ts">
	import type { Snippet } from 'svelte';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import Bar from './Bar.svelte';
	import Column from './Column.svelte';
	import type { PutAway } from './column';
	import ColumnRail from './ColumnRail.svelte';
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
		/** What the column is to whoever goes through the page by its parts: something beside what is read, or a way through it. */
		landmark: 'aside' | 'nav';
		/** What that part of the page is called: "Files". */
		label: string;
		/** What its own controls call it: "the file tree". */
		called: string;
		/** The name the tour lights it by, on screen or put away, written with lib/guide/tour.ts's tourStop. */
		'data-tour'?: string | undefined;
		testIds: TestIds;
		/** What heads the column, beside the way to put it away. */
		heading: Snippet;
		children: Snippet;
	}

	let { column, landmark, label, called, 'data-tour': tour, testIds, heading, children }: Props = $props();

	const putAway = $derived(`Put ${called} away`);
	const bringBack = $derived(`Bring ${called} back`);

	// The column and its way to its rail, while it is on screen; the rail, while it is put away
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

<!-- A column on the left of what is read, scrolling by itself, and put away to a rail where it stood, so the
	way back is where it went -->
{#if column.open}
	<Column
		bind:element={columnElement}
		side="left"
		width={column}
		{landmark}
		{label}
		resizing="Resize {called}"
		testIds={{ column: testIds.column, resize: testIds.resize }}
		data-tour={tour}
	>
		<Bar heads="column" testId={testIds.head}>
			{@render heading()}
			<div class="flex-1"></div>
			<IconButton
				bind:element={putAwayButton}
				tone="quiet"
				size="xs"
				label={putAway}
				testId={testIds.putAway}
				onclick={() => column.toggle()}
			>
				<Icon name="chevron" size="xs" pointing="left" />
			</IconButton>
		</Bar>
		<div class="cr-scroller min-h-0 flex-1 p-3">
			{@render children()}
		</div>
	</Column>
{:else}
	<ColumnRail
		bind:element={rail}
		label={bringBack}
		testId={testIds.bringBack}
		data-tour={tour}
		onclick={() => column.toggle()}
	/>
{/if}
