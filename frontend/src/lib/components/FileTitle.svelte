<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { DiffFile } from '$lib/types';
	import Count from '$lib/ui/Count.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import type { HeadingTag } from '$lib/ui/heading';
	import { fileStats } from '$lib/utils/file-stats';
	import ChangedLines from './ChangedLines.svelte';
	import FilePath from './FilePath.svelte';

	interface Props {
		/** The file, or the piece of one, the header is of. */
		file: DiffFile;
		/** What its name is to whoever goes through the page by its headings: a heading, or plain words where something else heads it. */
		element: Exclude<HeadingTag, 'h1'>;
		testId: string;
		/** Whether the review is of a change, which says what became of the file and how much it changes. */
		showsChange: boolean;
		/** How many threads hang on the lines the section draws. */
		threads: number;
		/** What is said right after the name: the round it changed since, the lines a step tells. */
		beside?: Snippet | undefined;
	}

	let { file, element, testId, showsChange, threads, beside }: Props = $props();
</script>

<!-- What a header of a file's lines says of the file, in the files and in a story alike: its name, what
	became of it in a word, how much it changes, and how many threads hang on what the section draws -->
<Heading tag={element} heads="piece" {testId}>
	<FilePath {file} />
</Heading>
{@render beside?.()}
{#if showsChange}
	<span class="cr-muted text-xs">{file.status}</span>
	<ChangedLines changed={fileStats(file)} />
{/if}
{#if threads > 0}
	<Count tone="reader" count={threads} testId="section-comment-count" />
{/if}
