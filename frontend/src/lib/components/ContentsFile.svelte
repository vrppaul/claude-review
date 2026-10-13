<script lang="ts">
	import type { Snippet } from 'svelte';
	import { useReview } from '$lib/review/context';
	import type { DiffFile } from '$lib/types';
	import { fileName } from '$lib/utils/paths';
	import StatusLetter from './StatusLetter.svelte';

	interface Props {
		/** The file the row names: its path, and what became of it. */
		file: DiffFile;
		/** What the section a reader who picks the row is taken to is known by. */
		opensAt: string;
		/** Whether the reader is in it now: the section being read is one this row stands for. */
		current: boolean;
		/** What is said at the row's end: how much the file changes, where else it is told, how much of it no step tells. */
		children: Snippet;
	}

	let { file, opensAt, current, children }: Props = $props();
	const review = useReview();
</script>

<!-- A file in a story's contents: what became of it, its name without its folders, cut where the
	column ends, and what is said of it. One press to where the story tells it -->
<li>
	<button
		type="button"
		data-testid="contents-file"
		class={['cr-contents-file', current && 'cr-current']}
		aria-current={current ? 'true' : undefined}
		title={file.path}
		onclick={() => review.sections.scrollTo(opensAt)}
	>
		<StatusLetter status={file.status} />
		<span class="truncate">{fileName(file.path)}</span>
		<span class="cr-contents-said">{@render children()}</span>
	</button>
</li>
