<script lang="ts">
	import type { Snippet } from 'svelte';
	import Count from '$lib/ui/Count.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import type { HeadingTag } from '$lib/ui/heading';
	import type { FileStats } from '$lib/utils/file-stats';
	import ChangedLines from './ChangedLines.svelte';
	import FilePath from './FilePath.svelte';

	interface Props {
		/** The path of the file, or of the piece of one, the header is of. */
		path: string;
		/** Where it was, for a file the change moved; none for any other. */
		formerPath: string | null;
		/** What its name is to whoever goes through the page by its headings: a heading, or plain words where something else heads it. */
		element: Exclude<HeadingTag, 'h1'>;
		testId: string;
		/** What became of the file, in a word: what the change did to it, or that it did not touch it; none where the review is not of a change. */
		became: string | null;
		/** How much the change changes it; none where it shows no change. */
		changed: FileStats | null;
		/** How many threads hang on the lines the section draws. */
		threads: number;
		/** What is said right after the name: the round it changed since, the lines a step tells. */
		beside?: Snippet | undefined;
	}

	let { path, formerPath, element, testId, became, changed, threads, beside }: Props = $props();
</script>

<!-- What a header of a file's lines says of the file, in the files, in a story and in a file read alone: its name,
	what became of it in a word, how much it changes, and how many threads hang on what the section draws -->
<Heading tag={element} heads="piece" {testId}>
	<FilePath {path} {formerPath} />
</Heading>
{@render beside?.()}
{#if became !== null}
	<span class="cr-muted text-xs">{became}</span>
{/if}
{#if changed !== null}
	<ChangedLines {changed} />
{/if}
{#if threads > 0}
	<Count tone="reader" count={threads} testId="section-comment-count" />
{/if}
