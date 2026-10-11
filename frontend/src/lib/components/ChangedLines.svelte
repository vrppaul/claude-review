<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();

	const stats = $derived(fileStats(file));
</script>

<!-- How much of a file changed, in the diff's own colours: the lines it added, and the lines it removed -->
<span class="font-mono text-xs whitespace-nowrap">
	<span class="text-(--cr-add-text)">+{stats.additions}</span>
	<span class="text-(--cr-del-text)">−{stats.deletions}</span>
</span>
