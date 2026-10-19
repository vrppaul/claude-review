<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { FileStatus } from '$lib/types';
	import Row from '$lib/ui/Row.svelte';
	import StatusLetter from './StatusLetter.svelte';

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
</script>

<!-- What became of the file, before its name, where the review says; the compiler is told again inside, as it
	cannot see the condition the snippet is handed under -->
{#snippet letter()}
	{#if status !== null}
		<StatusLetter {status} />
	{/if}
{/snippet}

<!-- Its marks, its threads, and how much it changes, at its end -->
{#snippet trailing()}
	{@render marks?.()}
	{#if threads > 0}
		<span data-testid="file-threads" class="badge badge-xs badge-primary">{threads}</span>
	{/if}
	{@render end?.()}
{/snippet}

<!-- A file in a column beside what is read, the tree of files or a story's contents: what became of it,
	its name, its threads and how much it changes. One press to where it is drawn -->
<li>
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
		leading={status === null ? undefined : letter}
		label={name}
		{trailing}
	/>
</li>
