<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { filesOutsideTheChange } from '$lib/review/files-way';
	import Heading from '$lib/ui/Heading.svelte';
	import { fileName, folderOf } from '$lib/utils/paths';
	import FileRow from './FileRow.svelte';

	const review = useReview();

	// The files the change did not touch, under its own, and the one of them read alone now
	const readAlone = $derived(review.views.fileReadAlone);
	const outside = $derived(filesOutsideTheChange(review.threads, review.diff, readAlone));
</script>

{#if outside.length > 0}
	<!-- Under the change's own files, those it did not touch that the reader reads or left something in: one
		press to read each alone -->
	<div data-testid="outside-files" class="mt-3 flex flex-col gap-1">
		<Heading tag="h3" heads="list" testId="outside-files-heading">Not in this change</Heading>
		<ul>
			{#each outside as path (path)}
				<FileRow
					testId="outside-file"
					status={null}
					current={path === readAlone}
					threads={review.threads.onLinesOf(path).length}
					title={path}
					onclick={() => void review.navigator.readAlone(path)}
				>
					{#snippet name()}
						{fileName(path)}
					{/snippet}
					{#snippet end()}
						<span class="cr-faint text-xs">{folderOf(path)}</span>
					{/snippet}
				</FileRow>
			{/each}
		</ul>
	</div>
{/if}
