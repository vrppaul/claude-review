<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import type { TouchedName } from '$lib/types';
	import NameRow from './NameRow.svelte';
	import type { LookupFromTheTree } from './tree-name-lookup';

	interface Props {
		/** The file the names are of. */
		path: string;
		/** The names the tree lists under it: those the change touched or the filter finds; none while they are folded. */
		names: readonly TouchedName[];
		/** What the tree's filter was typed, lit where it stands in a name. */
		sought: string;
		/** How many folders deep the names stand in the tree: a step past their file. */
		depth: number;
		/** The name the reader is in, whichever file's it is; none where they are in no name the tree lists. */
		nameInView: TouchedName | null;
		/** Whether the reader has finished with the file: its names step back with it. */
		viewed: boolean;
		/** The file's row as it is drawn, which takes the keyboard where a name's row that held it goes. */
		fileRow: HTMLButtonElement | undefined;
		/** Where the names are asked about from the icons on their rows. */
		lookup: LookupFromTheTree;
	}

	let { path, names, sought, depth, nameInView, viewed, fileRow, lookup }: Props = $props();
	const review = useReview();

	let list: HTMLElement | undefined = $state();

	// Whatever takes a name's row out — another reading's names on their way, the file's names folded or turned off,
	// the filter — takes with it the keyboard the row held. Looked at before the page redraws: the file's row then
	// takes it, and it is never left on nothing
	$effect.pre(() => {
		void names;
		if (list?.contains(document.activeElement)) focusWhatRemains(() => fileRow);
	});

	/** Go to where a name is defined, on the side its lines are numbered on, the name marked on its line. */
	function goTo(name: TouchedName) {
		void review.navigator.goToLine(
			path,
			{ side: name.side, number: name.line },
			{ column: name.column, name: name.name }
		);
	}
</script>

<!-- The names the change touched in a file, on branches off its letter: one press to where each is defined, and the
	icon at its end to where it is defined and used -->
{#if names.length > 0}
	<ul bind:this={list} data-testid="file-names">
		{#each names as name, position (name.name)}
			<NameRow
				{name}
				{sought}
				{depth}
				first={position === 0}
				current={nameInView === name}
				{viewed}
				onclick={() => goTo(name)}
				lookingUp={lookup.offers(name)
					? {
							open: lookup.isOpen(name),
							toggle: (icon: HTMLButtonElement) => lookup.toggle(path, name, icon, () => fileRow ?? null)
						}
					: undefined}
			/>
		{/each}
	</ul>
{/if}
