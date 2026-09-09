<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';
	import FileSection from './FileSection.svelte';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();

	const isSideBySide = $derived(diffStore.contentViewMode === 'side-by-side');
</script>

<div
	data-testid="diff-view"
	class="flex min-h-0 flex-1 flex-col bg-base-100 {isSideBySide
		? 'overflow-hidden'
		: 'overflow-auto'}"
>
	<FileSection {file} />
</div>
