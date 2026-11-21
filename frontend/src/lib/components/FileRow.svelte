<script lang="ts">
	import type { Snippet } from 'svelte';
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import type { FileStatus } from '$lib/types';
	import Count from '$lib/ui/Count.svelte';
	import FoldChevron from '$lib/ui/FoldChevron.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import RowWithAct from '$lib/ui/RowWithAct.svelte';
	import StatusLetter from '$lib/ui/StatusLetter.svelte';
	import { STATUS_LETTERS } from './status-letters';

	/** The names a row folds under it, as a folder folds its files: whether they are folded away, and how to fold or open them. */
	interface NamesFold {
		folded: boolean;
		toggle: () => void;
	}

	interface Props {
		testId: string;
		/** What the row announces itself by to whoever looks for the first of many: the tree's filter. */
		role?: string;
		/** How many folders deep it stands, which sets it in; at the top, where whatever lists it sets it in itself. */
		depth?: number;
		/** What became of the file, where the review is of a change; none where it is of files, or a transcript. */
		status: FileStatus | null;
		/** Whether the reader is in it now; never, for a file the view on screen does not draw. */
		current?: boolean;
		/** Whether the reader has finished with it: the row steps back. Never, where nothing says so. */
		viewed?: boolean;
		/** How many threads hang on the lines the row stands for. */
		threads: number;
		/** What the row is called in full, where its name is cut: the file's path. */
		title?: string;
		onclick: () => void;
		/** Its name, cut where the column ends. */
		name: Snippet;
		/** What is said after its name, before its threads: marks of what became of it since. */
		marks?: Snippet;
		/** What is said at its end: how much the file changes, where else it is told. */
		end?: Snippet;
		/** The names it folds under it, by the chevron at its end; none where it lists no names. */
		namesFold?: NamesFold | undefined;
		/** What hangs under it in the tree, handed the row as drawn: the names the change touched in it. */
		under?: Snippet<[HTMLButtonElement | undefined]>;
		/** The row itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
	}

	let {
		testId,
		role,
		depth = 0,
		status,
		current = false,
		viewed = false,
		threads,
		title,
		onclick,
		name,
		marks,
		end,
		namesFold,
		under,
		element = $bindable()
	}: Props = $props();

	// What the chevron that folds a file's names says it will do
	const FOLD_NAMES = 'Fold its names';
	const SHOW_NAMES = 'Show its names';

	// What became of the file, as its letter says it and its word for whoever cannot see the letter; none where the
	// review does not say
	const statusLetter = $derived(status === null ? null : { ...STATUS_LETTERS[status], said: status });

	// The chevron that folds its names, as it is drawn while it lists any
	let namesChevron: HTMLButtonElement | undefined = $state();

	// The chevron goes with the names it folds, another reading's on their way, and takes with it the keyboard it
	// held. Looked at before the page redraws: the row then takes it, and it is never left on nothing
	$effect.pre(() => {
		if (namesFold === undefined && namesChevron === document.activeElement) focusWhatRemains(() => element);
	});
</script>

<!-- Its marks, its threads, and how much it changes, at its end -->
{#snippet trailing()}
	{@render marks?.()}
	{#if threads > 0}
		<Count tone="reader" count={threads} testId="file-threads" />
	{/if}
	{@render end?.()}
{/snippet}

<!-- The chevron that folds its names, at its end while it lists any -->
{#snippet chevron()}
	{#if namesFold !== undefined}
		<IconButton
			bind:element={namesChevron}
			tone="quiet"
			size="xs"
			shape="square"
			label={namesFold.folded ? SHOW_NAMES : FOLD_NAMES}
			testId="{testId}-names-fold"
			aria-expanded={!namesFold.folded}
			onclick={namesFold.toggle}
		>
			<FoldChevron folded={namesFold.folded} />
		</IconButton>
	{/if}
{/snippet}

<!-- The row, led by what stands before its name, if anything does: one element while its file is listed, whether
	its names come or go, so the keyboard on it stays there -->
{#snippet row(leading: Snippet | undefined)}
	<RowWithAct
		names="path"
		{testId}
		data-role={role}
		{depth}
		{current}
		{viewed}
		aria-current={current ? 'true' : undefined}
		{title}
		{onclick}
		label={name}
		{trailing}
		{leading}
		act={chevron}
		actShown="always"
		bind:element
	/>
{/snippet}

<!-- A file in a column beside what is read, the tree of files or a story's contents: what became of it, where
	the review says, its name, its threads and how much it changes, and what hangs under it. One press to where it
	is drawn -->
<li>
	{#if statusLetter === null}
		{@render row(undefined)}
	{:else}
		<!-- Held as it is here, where it is known, for the letter drawn from it -->
		{@const drawn = statusLetter}
		{#snippet letter()}
			<StatusLetter {...drawn} />
		{/snippet}
		{@render row(letter)}
	{/if}
	{@render under?.(element)}
</li>
