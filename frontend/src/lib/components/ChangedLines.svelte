<script lang="ts">
	import type { FileStats } from '$lib/utils/file-stats';

	interface Props {
		/** How much changed: of one file, of a piece of one, or of several pieces added up. */
		changed: FileStats;
	}

	let { changed }: Props = $props();
</script>

<!-- How much changed, in the diff's own colours: the lines added, and the lines removed -->
<span class="font-mono text-xs whitespace-nowrap">
	<span class="text-(--cr-add-text)">+{changed.additions}</span>
	<span class="text-(--cr-del-text)">−{changed.deletions}</span>
</span>
