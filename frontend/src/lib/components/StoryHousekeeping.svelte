<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { useReview } from '$lib/review/context';
	import Row from '$lib/ui/Row.svelte';
	import { fileStats } from '$lib/utils/file-stats';
	import { fileName } from '$lib/utils/paths';
	import { counted, FILES } from '$lib/utils/words';
	import ChangedLines from './ChangedLines.svelte';
	import FileRow from './FileRow.svelte';

	interface Props {
		/** The files the agent called housekeeping, by their paths. */
		paths: string[];
		testId: string;
		/** How it is set where it stands: under the story, or under its contents. */
		class: ClassValue;
	}

	let { paths, testId, class: set }: Props = $props();
	const review = useReview();

	// Folded away until the reader asks: the story draws none of these files, and they are the least of it
	let folded = $state(true);
	const called = $derived(new Set(paths));
	// The files themselves, as the diff on screen holds them: each a way to where the files draw it
	const files = $derived(review.diff.files.filter((file) => called.has(file.path)));
</script>

<!-- What the agent called housekeeping: named, quiet and folded away. The story draws none of it; each
	file is a row as the tree of files draws it, its name as quiet as the row that folds it, and pressed,
	the files come on screen at it -->
<div data-testid={testId} class={set}>
	<Row names="title" testId="fold-housekeeping" {folded} onclick={() => (folded = !folded)}>
		{#snippet label()}
			<span class="cr-muted">Housekeeping · {counted(paths.length, FILES)}</span>
		{/snippet}
	</Row>
	{#if !folded}
		<ul>
			{#each files as file (file.path)}
				<FileRow
					testId="housekeeping-file"
					status={file.status}
					threads={review.threads.onLinesOf(file.path).length}
					title={file.path}
					onclick={() => review.navigator.showFile(file.path)}
				>
					{#snippet name()}
						<span class="cr-muted">{fileName(file.path)}</span>
					{/snippet}
					{#snippet end()}
						<ChangedLines changed={fileStats(file)} />
					{/snippet}
				</FileRow>
			{/each}
		</ul>
	{/if}
</div>
