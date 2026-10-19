<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { FileStatus } from '$lib/types';
	import Count from '$lib/ui/Count.svelte';
	import Row from '$lib/ui/Row.svelte';
	import StatusLetter from '$lib/ui/StatusLetter.svelte';
	import { STATUS_LETTERS } from './status-letters';

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
		end
	}: Props = $props();

	// What became of the file, as its letter says it and its word for whoever cannot see the letter; none where the
	// review does not say
	const statusLetter = $derived(status === null ? null : { ...STATUS_LETTERS[status], said: status });
</script>

<!-- Its marks, its threads, and how much it changes, at its end -->
{#snippet trailing()}
	{@render marks?.()}
	{#if threads > 0}
		<Count count={threads} testId="file-threads" />
	{/if}
	{@render end?.()}
{/snippet}

<!-- The row, led by what stands before its name, if anything does -->
{#snippet row(leading: Snippet | undefined)}
	<Row
		names="path"
		{testId}
		data-role={role}
		{depth}
		{current}
		{viewed}
		aria-current={current ? 'true' : undefined}
		{title}
		{onclick}
		{leading}
		label={name}
		{trailing}
	/>
{/snippet}

<!-- A file in a column beside what is read, the tree of files or a story's contents: what became of it, where
	the review says, its name, its threads and how much it changes. One press to where it is drawn -->
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
</li>
