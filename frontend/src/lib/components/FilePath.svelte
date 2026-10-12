<script lang="ts">
	import type { DiffFile } from '$lib/types';

	interface Props {
		/** The file a heading names: one that was moved says where it was, before where it is. */
		file: DiffFile;
	}

	let { file }: Props = $props();
</script>

<!-- A file's path as a heading says it, wherever its lines are drawn: whole among the files, or a piece of it in a story -->
{#if file.old_path}
	<!-- Moved: where it was, quieter than where it is -->
	<span class="cr-muted font-normal">{file.old_path} →</span>
{/if}
{file.path}
