<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import type { TourTarget } from '$lib/guide/tour';
	import type { PutAwayColumn } from '$lib/reader/page-layout.svelte';
	import EdgeGrip from './EdgeGrip.svelte';
	import Icon from './Icon.svelte';

	/** What the tests know each part of the column by, written whole where the column is drawn. */
	interface TestIds {
		column: string;
		resize: string;
		putAway: string;
		bringBack: string;
	}

	interface Props {
		/** Whether the column is on screen, and how wide the reader left it. */
		column: PutAwayColumn;
		/** What the column is to whoever goes through the page by its parts: something beside what is read, or a way through it. */
		landmark: 'aside' | 'nav';
		/** What that part of the page is called: "Files". */
		label: string;
		/** What its own controls call it: "the file tree". */
		called: string;
		/** The name the tour lights it by, on screen or put away, where the tour stops at it. */
		tour?: TourTarget;
		/** The ground it stands on. */
		class: ClassValue;
		testIds: TestIds;
		/** What heads the column, beside the way to put it away. */
		heading: Snippet;
		children: Snippet;
	}

	let { column, landmark, label, called, tour, class: ground, testIds, heading, children }: Props = $props();

	const putAway = $derived(`Put ${called} away`);
	const bringBack = $derived(`Bring ${called} back`);

	// The column and its way to its rail, while it is on screen; the rail, while it is put away
	let columnElement: HTMLElement | undefined = $state();
	let putAwayButton: HTMLElement | undefined = $state();
	let rail: HTMLElement | undefined = $state();

	// Put away or brought back, by its own control or by a key, the column takes with it whatever held
	// the keyboard in it: the control pressed, an entry. Looked at before the page redraws it: the
	// keyboard then goes to the control that undoes what was done, and is never left on nothing
	$effect.pre(() => {
		const open = column.open;
		const drawnBefore = open ? rail : columnElement;
		if (drawnBefore?.contains(document.activeElement)) focusWhatRemains(() => (open ? putAwayButton : rail));
	});
</script>

<!-- A column beside what is read: as wide as the reader left it, scrolling by itself, and put away
	to a rail where it stood, so the way back is where it went -->
{#if column.open}
	<svelte:element
		this={landmark}
		bind:this={columnElement}
		data-testid={testIds.column}
		data-tour={tour}
		aria-label={label}
		class={['cr-tree flex flex-col border-r border-base-300', ground]}
		style:--cr-tree-width="{column.width}px"
	>
		<!-- The column is on the left, so it grows rightward -->
		<EdgeGrip {column} grows="right" label="Resize {called}" testId={testIds.resize} />
		<div class="cr-scroller min-h-0 flex-1 p-3">
			<div class="mb-2 flex items-center gap-2">
				{@render heading()}
				<div class="flex-1"></div>
				<button
					bind:this={putAwayButton}
					type="button"
					data-testid={testIds.putAway}
					class="btn btn-ghost btn-xs px-1"
					title={putAway}
					aria-label={putAway}
					onclick={() => column.toggle()}
				>
					<Icon name="caret" class="h-3 w-3 rotate-180" />
				</button>
			</div>
			{@render children()}
		</div>
	</svelte:element>
{:else}
	<button
		bind:this={rail}
		type="button"
		data-testid={testIds.bringBack}
		data-tour={tour}
		class="cr-tree-rail"
		title={bringBack}
		aria-label={bringBack}
		onclick={() => column.toggle()}
	>
		<Icon name="caret" class="h-3 w-3" />
	</button>
{/if}
